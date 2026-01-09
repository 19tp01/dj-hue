"""WebSocket control server for DJ-Hue.

Exposes pattern engine control via WebSocket on localhost:9876.
Designed to run alongside the main MIDI loop in a separate thread.
"""

import asyncio
import json
import threading
from typing import TYPE_CHECKING

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
        host: str = "localhost",
        port: int = DEFAULT_PORT,
    ):
        self.pattern_engine = pattern_engine
        self.engine_state = engine_state
        self.midi_out = midi_out
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
            "blackout": self.pattern_engine._blackout,
            "patterns": self.pattern_engine.pattern_names,
            "palettes": self.pattern_engine.get_available_palettes(),
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
