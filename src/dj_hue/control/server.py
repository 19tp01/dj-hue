"""WebSocket control server for DJ-Hue.

Exposes pattern engine control via WebSocket on localhost:9876.
Designed to run alongside the main MIDI loop in a separate thread.
"""

import asyncio
import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from aiohttp import web, WSMsgType

if TYPE_CHECKING:
    import mido
    from dj_hue.patterns import PatternEngine, QuickAction

# Default port for control server
DEFAULT_PORT = 9876
STATUS_BROADCAST_HZ = 10
STATUS_INTERVAL = 1.0 / STATUS_BROADCAST_HZ


class ControlServer:
    """WebSocket server for remote control of DJ-Hue."""

    def __init__(
        self,
        pattern_engine: "PatternEngine",
        engine_state,  # EngineState from midi_pattern_mode
        midi_out: "mido.ports.BaseOutput | None" = None,
        hue_streamer: Any = None,  # HueStreamer for light config
        config_path: Path | None = None,  # Path to config.yaml
        host: str = "localhost",
        port: int = DEFAULT_PORT,
    ):
        self.pattern_engine = pattern_engine
        self.engine_state = engine_state
        self.midi_out = midi_out
        self.hue_streamer = hue_streamer
        self.config_path = config_path or Path("config.yaml")
        self.host = host
        self.port = port

        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._clients: set[web.WebSocketResponse] = set()
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle incoming WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self._clients.add(ws)
        print(f"[CONTROL] Client connected ({len(self._clients)} total)")

        try:
            # Send initial status
            status = self._get_status()
            await ws.send_json(status)

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_command(data, ws)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "message": "Invalid JSON"})
                elif msg.type == WSMsgType.ERROR:
                    print(f"[CONTROL] WebSocket error: {ws.exception()}")
        finally:
            self._clients.discard(ws)
            print(f"[CONTROL] Client disconnected ({len(self._clients)} total)")

        return ws

    async def _handle_command(self, data: dict, ws: web.WebSocketResponse) -> None:
        """Handle a command from client."""
        cmd_type = data.get("type")

        if cmd_type == "set_pattern":
            # Check queue mode
            with self.engine_state.lock:
                queue_mode = self.engine_state.queue_mode

            if queue_mode > 0:
                # Queue the pattern instead of switching immediately
                index = data.get("index")
                name = data.get("name")

                if name is not None:
                    # Find index by name
                    try:
                        index = self.pattern_engine.pattern_names.index(name)
                    except ValueError:
                        index = None

                if index is not None:
                    # Calculate target bar
                    with self.engine_state.lock:
                        current_bar = int(self.engine_state.beat_position // 4) + 1
                        target_bar = current_bar + queue_mode
                        self.engine_state.queued_pattern_index = index
                        self.engine_state.queue_target_bar = target_bar
                    await self._broadcast_status()
            else:
                # Immediate switch
                if "index" in data:
                    success = self.pattern_engine.set_pattern_by_index(data["index"])
                elif "name" in data:
                    success = self.pattern_engine.set_pattern(data["name"])
                else:
                    success = False
                if success:
                    await self._broadcast_status()

        elif cmd_type == "set_palette":
            name = data.get("name")  # None clears override
            self.pattern_engine.set_palette(name)
            await self._broadcast_status()

        elif cmd_type == "toggle_blackout":
            self.pattern_engine.toggle_blackout()
            await self._broadcast_status()

        elif cmd_type == "flash":
            from dj_hue.patterns import QuickAction
            duration = data.get("duration_beats", 0.5)
            self.pattern_engine.trigger_quick_action(QuickAction.flash(duration_beats=duration))

        elif cmd_type == "tap_tempo":
            self._send_midi_note(61)  # C#4 - tap tempo

        elif cmd_type == "sync":
            self._send_midi_note(60)  # C4 - sync/restart
            # Also reset our beat tracking
            with self.engine_state.lock:
                self.engine_state.beat_position = 0.0
                self.engine_state.beat_count = 1

        elif cmd_type == "start":
            self._send_midi_start()

        elif cmd_type == "stop":
            self._send_midi_stop()

        elif cmd_type == "get_status":
            status = self._get_status()
            await ws.send_json(status)

        elif cmd_type == "get_light_config":
            config = self._get_light_config()
            await ws.send_json(config)

        elif cmd_type == "save_light_config":
            light_order = data.get("light_order", [])
            custom_groups = data.get("custom_groups", {})
            zones = data.get("zones", {})
            success, message = self._save_light_config(light_order, custom_groups, zones)
            await ws.send_json({
                "type": "light_config_saved",
                "success": success,
                "message": message,
            })

        elif cmd_type == "identify_light":
            index = data.get("index", 0)
            await self._identify_light(index)

        elif cmd_type == "set_zone_brightness":
            zone = data.get("zone")
            value = data.get("value", 1.0)
            # Clamp to 0-1 range
            value = max(0.0, min(1.0, float(value)))
            if zone in ("ceiling", "perimeter", "ambient"):
                with self.engine_state.lock:
                    self.engine_state.zone_brightness[zone] = value
                await self._broadcast_status()

        elif cmd_type == "fade_out":
            import time
            with self.engine_state.lock:
                self.engine_state.fade_active = True
                self.engine_state.fade_start_time = time.time()
            await self._broadcast_status()

        elif cmd_type == "set_queue_mode":
            mode = data.get("mode", 0)
            if mode in (0, 1, 2):
                with self.engine_state.lock:
                    self.engine_state.queue_mode = mode
                    # Clear any pending queue if turning off
                    if mode == 0:
                        self.engine_state.queued_pattern_index = None
                        self.engine_state.queue_target_bar = None
                await self._broadcast_status()

        # Pattern CRUD operations
        elif cmd_type == "get_pattern_list":
            patterns = self._get_pattern_list()
            await ws.send_json({"type": "pattern_list", "patterns": patterns})

        elif cmd_type == "get_pattern_source":
            name = data.get("name")
            result = self._get_pattern_source(name)
            await ws.send_json(result)

        elif cmd_type == "save_pattern":
            result = self._save_pattern(data)
            await ws.send_json(result)
            if result.get("success"):
                # Reload patterns and broadcast updated status
                self.pattern_engine.reload_strudel_patterns()
                await self._broadcast_status()

        elif cmd_type == "delete_pattern":
            name = data.get("name")
            result = self._delete_pattern(name)
            await ws.send_json(result)
            if result.get("success"):
                # Reload patterns and broadcast updated status
                self.pattern_engine.reload_strudel_patterns()
                await self._broadcast_status()

        elif cmd_type == "validate_pattern":
            body = data.get("body", "")
            result = self._validate_pattern(body)
            await ws.send_json(result)

    def _send_midi_note(self, note: int, velocity: int = 127, channel: int = 0) -> None:
        """Send MIDI note on/off pair."""
        if self.midi_out is None:
            return
        import mido
        self.midi_out.send(mido.Message("note_on", note=note, velocity=velocity, channel=channel))
        self.midi_out.send(mido.Message("note_off", note=note, velocity=0, channel=channel))

    def _send_midi_start(self) -> None:
        """Send MIDI Start message (0xFA)."""
        if self.midi_out is None:
            return
        import mido
        self.midi_out.send(mido.Message("start"))

    def _send_midi_stop(self) -> None:
        """Send MIDI Stop message (0xFC)."""
        if self.midi_out is None:
            return
        import mido
        self.midi_out.send(mido.Message("stop"))

    def _get_status(self) -> dict:
        """Get current engine status."""
        with self.engine_state.lock:
            beat_position = self.engine_state.beat_position
            bpm = self.engine_state.bpm
            zone_brightness = dict(self.engine_state.zone_brightness)
            fade_active = self.engine_state.fade_active
            queue_mode = self.engine_state.queue_mode
            queued_pattern_index = self.engine_state.queued_pattern_index
            queue_target_bar = self.engine_state.queue_target_bar

        # Calculate bar and beat
        beat_in_bar = int(beat_position % 4) + 1
        bar = int(beat_position // 4) + 1

        return {
            "type": "status",
            "bpm": round(bpm, 1),
            "beat_position": round(beat_position, 2),
            "bar": bar,
            "beat_in_bar": beat_in_bar,
            "pattern_index": self.pattern_engine._current_pattern_index,
            "pattern_name": self.pattern_engine.get_current_pattern_name(),
            "palette_name": self.pattern_engine.get_active_palette_name(),
            "palette_override": self.pattern_engine.get_palette_override() is not None,
            "zone_brightness": zone_brightness,
            "fade_active": fade_active,
            "queue_mode": queue_mode,
            "queued_pattern_index": queued_pattern_index,
            "queue_target_bar": queue_target_bar,
            "patterns": self.pattern_engine.get_pattern_info(),
            "palettes": self.pattern_engine.get_available_palettes(),
        }

    def _get_light_config(self) -> dict:
        """Get light configuration for settings UI."""
        # Load current config from file
        light_order: list[str] = []
        custom_groups: dict[str, list[str]] = {}
        zones: dict[str, list[str]] = {}

        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = yaml.safe_load(f) or {}
                hue_config = config.get("hue", {})
                light_order = hue_config.get("light_order", [])
                custom_groups = hue_config.get("custom_groups", {})
                zones = hue_config.get("zones", {})
            except Exception as e:
                print(f"[CONTROL] Error loading config: {e}")

        # Get light info from streamer
        lights: list[dict] = []
        groups: dict[str, list[int]] = {}

        if self.hue_streamer:
            lights = self.hue_streamer.get_light_info()
            groups = self.hue_streamer.light_groups

        return {
            "type": "light_config",
            "lights": lights,
            "groups": groups,
            "light_order": light_order,
            "custom_groups": custom_groups,
            "zones": zones,
        }

    def _save_light_config(
        self,
        light_order: list[str],
        custom_groups: dict[str, list[str]],
        zones: dict[str, list[str]] | None = None,
    ) -> tuple[bool, str]:
        """Save light configuration to config.yaml.

        Returns (success, message) tuple.
        """
        try:
            # Load existing config
            config: dict[str, Any] = {}
            if self.config_path.exists():
                with open(self.config_path) as f:
                    config = yaml.safe_load(f) or {}

            # Update light config sections (under "hue" section where CLI reads from)
            if "hue" not in config:
                config["hue"] = {}
            config["hue"]["light_order"] = light_order
            config["hue"]["custom_groups"] = custom_groups
            if zones is not None:
                config["hue"]["zones"] = zones

            # Write atomically (write to temp file, then rename)
            temp_path = self.config_path.with_suffix(".yaml.tmp")
            with open(temp_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            temp_path.replace(self.config_path)

            return True, "Configuration saved. Restart DJ-Hue to apply changes."

        except Exception as e:
            print(f"[CONTROL] Error saving config: {e}")
            return False, f"Failed to save configuration: {e}"

    async def _identify_light(self, index: int) -> None:
        """Flash a light to identify it physically.

        Sets a flag in engine_state that the render loop checks.
        The render loop will flash the light white for ~1 second.
        """
        import time

        # Set the identify flag - render loop will handle the actual flashing
        with self.engine_state.lock:
            self.engine_state.identify_light_index = index
            self.engine_state.identify_until = time.time() + 1.0  # Flash for 1 second

        print(f"[CONTROL] Identifying light {index}")

    def _get_pattern_list(self) -> list[dict]:
        """Get list of all patterns with metadata."""
        from dj_hue.patterns.loader import get_pattern_source

        patterns_dir = self.pattern_engine._patterns_dir
        if not patterns_dir or not patterns_dir.exists():
            return []

        result = []
        for pattern_file in sorted(patterns_dir.glob("*.pattern")):
            try:
                source = get_pattern_source(pattern_file)
                result.append({
                    "filename": pattern_file.name,
                    "name": source["name"],
                    "description": source["description"],
                    "tags": source["tags"],
                    "palette": source["palette"],
                    "category": source["category"],
                })
            except Exception as e:
                print(f"[CONTROL] Error reading {pattern_file}: {e}")

        return result

    def _get_pattern_source(self, name: str) -> dict:
        """Get full source of a pattern by name."""
        from dj_hue.patterns.loader import get_pattern_source

        patterns_dir = self.pattern_engine._patterns_dir
        if not patterns_dir:
            return {"type": "pattern_source", "success": False, "error": "No patterns directory"}

        # Find pattern file by name
        for pattern_file in patterns_dir.glob("*.pattern"):
            try:
                source = get_pattern_source(pattern_file)
                if source["name"] == name:
                    return {
                        "type": "pattern_source",
                        "success": True,
                        "filename": pattern_file.name,
                        **source,
                    }
            except Exception:
                continue

        return {"type": "pattern_source", "success": False, "error": f"Pattern '{name}' not found"}

    def _save_pattern(self, data: dict) -> dict:
        """Save a pattern (create or update)."""
        import re
        from dj_hue.patterns.loader import save_pattern, get_pattern_source

        patterns_dir = self.pattern_engine._patterns_dir
        if not patterns_dir:
            return {"type": "pattern_saved", "success": False, "error": "No patterns directory"}

        name = data.get("name", "").strip()
        if not name:
            return {"type": "pattern_saved", "success": False, "error": "Pattern name required"}

        description = data.get("description", "")
        tags = data.get("tags", [])
        palette = data.get("palette")
        category = data.get("category", "Chill")
        body = data.get("body", "")

        # If updating existing pattern, find its file
        filename = data.get("filename")
        if filename:
            file_path = patterns_dir / filename
        else:
            # Create new filename from name
            slug = name.lower()
            slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
            file_path = patterns_dir / f"{slug}.pattern"

            # Handle collision
            if file_path.exists():
                # Check if it's the same pattern (by name)
                try:
                    existing = get_pattern_source(file_path)
                    if existing["name"] != name:
                        # Different pattern, need unique filename
                        i = 2
                        while True:
                            file_path = patterns_dir / f"{slug}_{i}.pattern"
                            if not file_path.exists():
                                break
                            i += 1
                except Exception:
                    pass

        try:
            # If updating, try to preserve existing body and category if not provided
            if file_path.exists():
                try:
                    existing = get_pattern_source(file_path)
                    if not body:
                        body = existing.get("body", "")
                    if not category:
                        category = existing.get("category", "Chill")
                except Exception:
                    pass

            if not body:
                body = 'light("all").color("white")'

            save_pattern(file_path, name, body, description, tags, palette, category)
            return {
                "type": "pattern_saved",
                "success": True,
                "filename": file_path.name,
                "message": f"Pattern '{name}' saved",
            }
        except Exception as e:
            return {"type": "pattern_saved", "success": False, "error": str(e)}

    def _delete_pattern(self, name: str) -> dict:
        """Delete a pattern by name."""
        from dj_hue.patterns.loader import get_pattern_source

        patterns_dir = self.pattern_engine._patterns_dir
        if not patterns_dir:
            return {"type": "pattern_deleted", "success": False, "error": "No patterns directory"}

        # Find and delete pattern file
        for pattern_file in patterns_dir.glob("*.pattern"):
            try:
                source = get_pattern_source(pattern_file)
                if source["name"] == name:
                    pattern_file.unlink()
                    return {
                        "type": "pattern_deleted",
                        "success": True,
                        "message": f"Pattern '{name}' deleted",
                    }
            except Exception:
                continue

        return {"type": "pattern_deleted", "success": False, "error": f"Pattern '{name}' not found"}

    def _validate_pattern(self, body: str) -> dict:
        """Validate pattern DSL code without saving."""
        import ast

        if not body or not body.strip():
            return {"type": "pattern_validated", "valid": False, "error": "Pattern code is empty"}

        try:
            # Import strudel module and build namespace with all exports (same as loader.py)
            from dj_hue.patterns import strudel
            from dj_hue.patterns.strudel import LightPattern

            # Build namespace with all strudel exports
            context = {n: getattr(strudel, n) for n in strudel.__all__}

            # Parse as Python code (same approach as loader.py)
            tree = ast.parse(body.strip(), mode="exec")

            if not tree.body:
                return {"type": "pattern_validated", "valid": False, "error": "Pattern code is empty"}

            # If the last statement is an expression, wrap it to capture the result
            last_stmt = tree.body[-1]
            if isinstance(last_stmt, ast.Expr):
                assign = ast.Assign(
                    targets=[ast.Name(id="_result", ctx=ast.Store())],
                    value=last_stmt.value,
                )
                ast.copy_location(assign, last_stmt)
                tree.body[-1] = assign
                ast.fix_missing_locations(tree)

            # Execute the code
            exec(compile(tree, "<pattern>", "exec"), context)

            result = context.get("_result")
            if not isinstance(result, LightPattern):
                return {
                    "type": "pattern_validated",
                    "valid": False,
                    "error": "Code must return a LightPattern (use light(), stack(), or cat())",
                }

            return {"type": "pattern_validated", "valid": True}

        except SyntaxError as e:
            line = e.lineno if e.lineno else "?"
            msg = e.msg if e.msg else str(e)
            return {
                "type": "pattern_validated",
                "valid": False,
                "error": f"Syntax error on line {line}: {msg}",
            }
        except NameError as e:
            # Extract name from error message for compatibility
            error_str = str(e)
            return {
                "type": "pattern_validated",
                "valid": False,
                "error": f"Unknown name: {error_str}",
            }
        except Exception as e:
            return {
                "type": "pattern_validated",
                "valid": False,
                "error": str(e),
            }

    async def _broadcast_status(self) -> None:
        """Broadcast status to all connected clients."""
        if not self._clients:
            return

        status = self._get_status()
        dead_clients = set()

        for ws in self._clients:
            try:
                await ws.send_json(status)
            except Exception:
                dead_clients.add(ws)

        self._clients -= dead_clients

    async def _status_loop(self) -> None:
        """Periodically broadcast status to all clients."""
        while self._running:
            await self._broadcast_status()
            await asyncio.sleep(STATUS_INTERVAL)

    async def _start_async(self) -> None:
        """Start the server (async)."""
        self._app = web.Application()
        self._app.router.add_get("/ws", self._handle_websocket)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        self._running = True
        print(f"[CONTROL] WebSocket server running on ws://{self.host}:{self.port}/ws")

        # Start status broadcast loop
        asyncio.create_task(self._status_loop())

    async def _stop_async(self) -> None:
        """Stop the server (async)."""
        self._running = False

        # Close all client connections
        for ws in list(self._clients):
            await ws.close()
        self._clients.clear()

        if self._runner:
            await self._runner.cleanup()

    def start_in_thread(self) -> threading.Thread:
        """Start the control server in a background thread.

        Returns the thread so caller can join it on shutdown.
        """
        def run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            try:
                self._loop.run_until_complete(self._start_async())
                self._loop.run_forever()
            finally:
                self._loop.run_until_complete(self._stop_async())
                self._loop.close()

        thread = threading.Thread(target=run, daemon=True, name="ControlServer")
        thread.start()
        return thread

    def stop(self) -> None:
        """Signal the server to stop."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
