"""MIDI Clock to Hue lights with PatternEngine - Pattern-based control.

Uses MIDI Clock output from Ableton (works with Tempo Follower enabled).
Integrates with the PatternEngine for pattern-based lighting control.
"""

import os
import select
import signal
import struct
import sys
import termios
import threading
import time
import tty
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import mido

from dj_hue.patterns import PatternEngine, PatternLoader, LightSetup, LightGroup, QuickAction, ColorPalette
from dj_hue.patterns.presets import get_strudel_presets


# Render thread runs at 50 Hz to match Zigbee transmission rate
RENDER_HZ = 50
RENDER_INTERVAL = 1.0 / RENDER_HZ

# MIDI Clock sends 24 ticks per quarter note (beat)
TICKS_PER_BEAT = 24

# Anticipation: trigger lights this many ticks BEFORE the beat
ANTICIPATION_TICKS = 6


@dataclass
class LightState:
    """RGB state for a light."""
    light_id: int
    r: int
    g: int
    b: int


class HueStreamer:
    """Stream color updates to Hue lights via Entertainment API."""

    def __init__(
        self,
        bridge_ip: str,
        username: str,
        clientkey: str,
        entertainment_area_id: str,
    ):
        self.bridge_ip = bridge_ip
        self.username = username
        self.clientkey = clientkey
        self.entertainment_area_id = entertainment_area_id

        self._streaming = None
        self._bridge = None
        self._entertainment = None
        self._running = False
        self._lock = threading.Lock()
        self._num_channels = 0
        self._light_groups: dict[str, list[int]] = {}  # Group name -> channel indices

    def start(self) -> None:
        """Start the streaming connection."""
        from hue_entertainment_pykit import Bridge, Entertainment, Streaming

        self._bridge = Bridge(
            ip_address=self.bridge_ip,
            username=self.username,
            clientkey=self.clientkey,
            hue_app_id=self.username,
        )

        self._entertainment = Entertainment(self._bridge)
        ent_configs_dict = self._entertainment.get_entertainment_configs()
        ent_conf_repo = self._entertainment.get_ent_conf_repo()

        target_config = None
        for config_id, config in ent_configs_dict.items():
            if (
                config_id == self.entertainment_area_id
                or config.id == self.entertainment_area_id
            ):
                target_config = config
                break

        if target_config is None:
            available = list(ent_configs_dict.keys())
            raise ValueError(
                f"Entertainment area '{self.entertainment_area_id}' not found. "
                f"Available: {available}"
            )

        # Count total channels (some lights like OmniGlow have multiple segments)
        self._num_channels = len(target_config.channels)

        # Detect groups based on shared entertainment service RIDs
        # Multi-segment lights (like OmniGlow) have multiple channels with the same RID
        rid_to_channels: dict[str, list[int]] = {}
        for i, channel in enumerate(target_config.channels):
            for member in channel.members:
                rid = member.service.rid
                if rid not in rid_to_channels:
                    rid_to_channels[rid] = []
                rid_to_channels[rid].append(i)

        # Build groups: "strip" for multi-segment lights, "lamps" for singles
        strip_channels = []
        lamp_channels = []
        for rid, channels in rid_to_channels.items():
            if len(channels) > 1:
                strip_channels.extend(channels)
            else:
                lamp_channels.extend(channels)

        self._light_groups = {
            "all": list(range(self._num_channels)),
            "strip": sorted(strip_channels),
            "lamps": sorted(lamp_channels),
        }

        # Global odd/even groups (for patterns that alternate all lights)
        self._light_groups["odd"] = [c for c in range(self._num_channels) if c % 2 == 1]
        self._light_groups["even"] = [c for c in range(self._num_channels) if c % 2 == 0]

        # Also create odd/even within each group for patterns that need it
        self._light_groups["strip_odd"] = [c for c in self._light_groups["strip"] if c % 2 == 1]
        self._light_groups["strip_even"] = [c for c in self._light_groups["strip"] if c % 2 == 0]
        self._light_groups["lamps_odd"] = [c for c in self._light_groups["lamps"] if c % 2 == 1]
        self._light_groups["lamps_even"] = [c for c in self._light_groups["lamps"] if c % 2 == 0]

        # Left/right splits (for compatibility with existing patterns)
        mid = self._num_channels // 2
        self._light_groups["left"] = list(range(mid))
        self._light_groups["right"] = list(range(mid, self._num_channels))

        self._streaming = Streaming(self._bridge, target_config, ent_conf_repo)
        self._streaming.set_color_space("rgb")
        self._streaming.start_stream()
        self._running = True

        print(f"[HUE] Streaming to {self._num_channels} channels")
        print(f"[HUE] Groups: strip={self._light_groups['strip']}, lamps={self._light_groups['lamps']}")

    def stop(self) -> None:
        """Stop the streaming connection."""
        self._running = False
        if self._streaming:
            try:
                self._streaming.stop_stream()
            except Exception:
                pass
            self._streaming = None

    @property
    def light_count(self) -> int:
        return self._num_channels

    @property
    def light_groups(self) -> dict[str, list[int]]:
        """Get detected light groups (strip, lamps, etc.)."""
        return self._light_groups


class EngineState:
    """Thread-safe shared state between MIDI and render threads."""

    def __init__(self):
        self.lock = threading.Lock()
        self.beat_position = 0.0
        self.bpm = 120.0
        self.beat_count = 0
        self.running = True


def rgb_to_rgb16(r: float, g: float, b: float) -> tuple[int, int, int]:
    """Convert RGB floats (0.0-1.0) to RGB16 (0-65535)."""
    return (
        int(max(0.0, min(1.0, r)) * 65535),
        int(max(0.0, min(1.0, g)) * 65535),
        int(max(0.0, min(1.0, b)) * 65535),
    )


def render_loop(
    engine_state: EngineState,
    streaming,  # Direct Streaming object from hue-entertainment-pykit
    pattern_engine: PatternEngine,
    num_lights: int,
):
    """Dedicated thread for smooth Hue updates at fixed rate.

    Sends ALL lights in a SINGLE batched DTLS message for minimal latency.
    """
    print(f"[RENDER] Started at {RENDER_HZ} Hz")

    # Access internals for direct socket access
    streaming_service = streaming._streaming_service
    dtls_socket = streaming_service._dtls_service.get_socket()

    # Stop the library's background threads to prevent interference
    print("[RENDER] Stopping library's background threads...")
    streaming_service._is_connection_alive = False
    time.sleep(1.5)
    streaming_service._is_connection_alive = True
    print("[RENDER] Library threads stopped, we have exclusive socket access")

    # Pre-build the message header
    protocol_name = "HueStream".encode("utf-8")
    version = struct.pack(">BB", 0x02, 0x00)
    sequence_id = struct.pack(">B", 0x07)
    reserved = b"\x00\x00"
    color_space = struct.pack(">B", 0x00)  # RGB
    reserved2 = b"\x00"
    entertainment_id = streaming_service._entertainment_config.id.encode("utf-8")

    header = protocol_name + version + sequence_id + reserved + color_space + reserved2 + entertainment_id

    # Timing diagnostics
    frame_count = 0
    last_report = time.time()
    last_frame_end = time.time()

    while engine_state.running:
        frame_start = time.time()

        # Get beat state
        with engine_state.lock:
            beat_pos = engine_state.beat_position
            bpm = engine_state.bpm

        # Update pattern engine with MIDI clock position
        pattern_engine.beat_clock.beat_position = beat_pos
        pattern_engine.beat_clock.bpm = bpm

        # Compute colors from pattern engine
        colors = pattern_engine.compute_colors()

        # Convert to light colors list
        light_colors = []
        for channel_id in range(num_lights):
            rgb = colors.get(channel_id)
            if rgb:
                light_colors.append((rgb.r / 255.0, rgb.g / 255.0, rgb.b / 255.0))
            else:
                light_colors.append((0.0, 0.0, 0.0))

        # Send to lights via direct socket
        for channel_id, (r, g, b) in enumerate(light_colors):
            r16, g16, b16 = rgb_to_rgb16(r, g, b)
            channel_data = struct.pack(">B", channel_id) + struct.pack(">HHH", r16, g16, b16)
            message = header + channel_data
            try:
                dtls_socket.send(message)
            except Exception:
                pass  # Suppress errors to keep UI clean
        streaming_service._last_message = message

        frame_count += 1

        # Frame counting (for diagnostics if needed)
        now = time.time()
        if now - last_report >= 5.0:
            frame_count = 0
            last_report = now

        # Precise timing
        elapsed = time.time() - frame_start
        sleep_time = RENDER_INTERVAL - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

        last_frame_end = time.time()

    print("[RENDER] Stopped")


def load_config():
    """Load Hue config from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config not found: {config_path}\n" "Run 'dj-hue --setup' first."
        )

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config.get("hue", {})


class KeyboardListener:
    """Non-blocking keyboard input listener."""

    def __init__(self):
        self.last_key = None
        self._running = False
        self._thread = None
        self._old_settings = None

    def start(self):
        """Start listening for keyboard input."""
        self._running = True
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self):
        """Listen for keypresses in background thread."""
        while self._running:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)
                self.last_key = key

    def get_key(self):
        """Get last pressed key (or None)."""
        key = self.last_key
        self.last_key = None
        return key

    def stop(self):
        """Stop listening and restore terminal."""
        self._running = False
        if self._old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)


# ANSI escape codes for terminal control
CLEAR_SCREEN = "\033[2J"
CURSOR_HOME = "\033[H"
CLEAR_LINE = "\033[K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def get_pattern_display_name(pattern_engine: PatternEngine, name: str) -> str:
    """Get display name for a pattern (handles both classic and Strudel)."""
    # Check if it's a Strudel pattern
    if name in pattern_engine._strudel_patterns:
        return name
    # Otherwise try to get the Pattern object's display name
    pattern = pattern_engine.get_pattern(name)
    return pattern.name if pattern else name


def draw_interface(pattern_engine: PatternEngine, bpm: float, bar: int, beat: int, message: str = ""):
    """Draw the static interface."""
    current_name = pattern_engine._pattern_names[pattern_engine._current_pattern_index]
    current_display = get_pattern_display_name(pattern_engine, current_name)
    is_strudel = current_name in pattern_engine._strudel_patterns

    # Build the interface
    lines = []
    lines.append(f"{BOLD}DJ-HUE{RESET} │ {bpm:.0f} BPM │ Bar {bar} Beat {beat}")
    lines.append("─" * 50)

    # Current pattern (highlighted)
    pattern_type = "(Strudel)" if is_strudel else ""
    lines.append(f"{BOLD}Pattern:{RESET} {current_display} {DIM}{pattern_type}{RESET}")
    lines.append("")

    # Pattern list (first 9)
    lines.append(f"{DIM}Patterns [1-9]:{RESET}")
    for i, name in enumerate(pattern_engine.pattern_names[:9]):
        display_name = get_pattern_display_name(pattern_engine, name)
        is_current = (i == pattern_engine._current_pattern_index)
        marker = "▶" if is_current else " "
        line = f"  {marker} {i+1}: {display_name}"
        if is_current:
            line = f"{BOLD}{line}{RESET}"
        lines.append(line)

    # Show indicator if there are more patterns
    total = len(pattern_engine.pattern_names)
    if total > 9:
        lines.append(f"  {DIM}... +{total - 9} more (press p){RESET}")

    lines.append("")
    lines.append(f"{DIM}[/] prev/next  [space] sync  [b] blackout  [f] flash  [p] patterns  [q] quit{RESET}")

    # Message line
    if message:
        lines.append("")
        lines.append(f"  {message}")

    # Clear and draw
    output = CURSOR_HOME + CLEAR_SCREEN
    output += "\n".join(lines)
    print(output, flush=True)


def print_pattern_selector(pattern_engine: PatternEngine) -> None:
    """Print pattern selection menu with all available patterns."""
    patterns = pattern_engine.pattern_names
    current_idx = pattern_engine._current_pattern_index

    output = CURSOR_HOME + CLEAR_SCREEN
    lines = []
    lines.append(f"{BOLD}PATTERN SELECTOR{RESET}")
    lines.append("─" * 50)
    lines.append(f"{DIM}Type number + Enter, or Escape to cancel{RESET}")
    lines.append("")

    for i, name in enumerate(patterns):
        display_name = get_pattern_display_name(pattern_engine, name)
        is_strudel = name in pattern_engine._strudel_patterns
        marker = "▶" if i == current_idx else " "
        tag = f"{DIM}(S){RESET}" if is_strudel else ""
        line = f"  {marker} {i + 1:2d}. {display_name} {tag}"
        if i == current_idx:
            line = f"{BOLD}  {marker} {i + 1:2d}. {display_name}{RESET} {tag}"
        lines.append(line)

    lines.append("")
    lines.append("─" * 50)

    print(output + "\n".join(lines), flush=True)


def pattern_selector_input(pattern_engine: PatternEngine, keyboard: "KeyboardListener") -> bool:
    """
    Handle pattern selector input mode.

    Returns True if a pattern was selected, False if cancelled.
    """
    print_pattern_selector(pattern_engine)
    print("Enter pattern number: ", end="", flush=True)

    input_buffer = ""
    while True:
        key = keyboard.get_key()
        if key is None:
            time.sleep(0.05)
            continue

        # Escape to cancel
        if key == "\x1b":  # Escape
            print("\n[Cancelled]")
            return False

        # Enter to confirm
        if key in ("\n", "\r"):
            if input_buffer:
                try:
                    idx = int(input_buffer) - 1
                    if pattern_engine.set_pattern_by_index(idx):
                        pattern = pattern_engine.current_pattern
                        print(f"\n>>> Selected: {pattern.name}")
                        return True
                    else:
                        print(f"\n[Invalid pattern number: {input_buffer}]")
                        return False
                except ValueError:
                    print(f"\n[Invalid input: {input_buffer}]")
                    return False
            else:
                print("\n[Cancelled]")
                return False

        # Backspace
        if key in ("\x7f", "\b"):
            if input_buffer:
                input_buffer = input_buffer[:-1]
                print("\b \b", end="", flush=True)
            continue

        # Number input
        if key.isdigit():
            input_buffer += key
            print(key, end="", flush=True)
            continue

        # Quick select: if single digit entered and valid, select immediately
        if len(input_buffer) == 1 and input_buffer.isdigit():
            idx = int(input_buffer) - 1
            if 0 <= idx < len(pattern_engine.pattern_names):
                # Give a moment to type more digits for patterns 10+
                pass


def main():
    """Main MIDI Clock to Hue with PatternEngine."""
    print("=" * 60)
    print("  MIDI Clock -> Hue Lights (Pattern Mode)")
    print("=" * 60)

    # Load config and start Hue
    hue_config = load_config()
    hue = HueStreamer(
        bridge_ip=hue_config["bridge_ip"],
        username=hue_config["username"],
        clientkey=hue_config["clientkey"],
        entertainment_area_id=hue_config["entertainment_area_id"],
    )
    hue.start()

    # Initialize pattern engine with detected groups from Hue
    num_lights = hue.light_count
    light_setup = LightSetup(name="hue_auto", total_lights=num_lights)

    # Add detected groups (strip, lamps, etc.)
    for group_name, indices in hue.light_groups.items():
        light_setup.add_group(LightGroup(name=group_name, light_indices=indices))

    # Auto-detect zones from group names
    ceiling_indices = hue.light_groups.get("lamps", [])
    perimeter_indices = hue.light_groups.get("strip", [])
    print(f"[ZONES] Detected ceiling={ceiling_indices}, perimeter={perimeter_indices}")

    if ceiling_indices and perimeter_indices:
        from dj_hue.patterns.common.zones import ZoneConfig
        zone_config = ZoneConfig.create_dual_zone(
            ceiling_indices=list(ceiling_indices),
            perimeter_indices=list(perimeter_indices)
        )
        light_setup.zone_config = zone_config
        print(f"[ZONES] Created dual-zone config")
    else:
        print(f"[ZONES] Missing zones - spatial patterns will be disabled")

    pattern_engine = PatternEngine(light_setup=light_setup)

    # Setup pattern loader for hot-reload
    patterns_dir = Path("patterns")
    loader: Optional[PatternLoader] = None
    if patterns_dir.exists():
        loader = PatternLoader(
            patterns_dir=patterns_dir,
            on_reload=lambda name, p: pattern_engine.register_pattern(name, p),
        )
        loader.load_all()
        loader.start_watching()
        print(f"[PATTERNS] Watching: {patterns_dir}")

    # Register Strudel patterns
    strudel_presets = get_strudel_presets()
    for name, (pattern, description) in strudel_presets.items():
        pattern_engine.register_strudel_pattern(name, pattern, description)
    print(f"[PATTERNS] Loaded {len(strudel_presets)} Strudel patterns")

    # Load spatial patterns (if zones are configured)
    if light_setup.zone_config:
        spatial_count = pattern_engine.load_spatial_presets()
        print(f"[PATTERNS] Loaded {spatial_count} spatial patterns")

    # Shared state between MIDI and render threads
    engine_state = EngineState()

    # Start render thread
    render_thread = threading.Thread(
        target=render_loop,
        args=(engine_state, hue._streaming, pattern_engine, num_lights),
        daemon=True,
    )
    render_thread.start()

    # Create virtual MIDI port
    port_name = "DJ-Hue Clock"

    keyboard = KeyboardListener()

    # UI state
    ui_message = "Waiting for MIDI clock..."
    ui_bar = 1
    ui_beat = 1
    ui_bpm = 120.0

    def signal_handler(sig, frame):
        engine_state.running = False
        print("\n[SHUTDOWN] Stopping...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        keyboard.start()
        print(HIDE_CURSOR, end="", flush=True)

        # Open MIDI output port to send signals to Ableton
        # Try IAC Driver first (more reliable), fall back to virtual port
        midi_out = None
        for p in mido.get_output_names():
            if 'IAC' in p:
                midi_out = mido.open_output(p)
                print(f"[MIDI] Output port: {p}")
                break
        if midi_out is None:
            midi_out = mido.open_output(port_name + " Out", virtual=True)
            print(f"[MIDI] Output port: {port_name} Out (virtual)")

        with mido.open_input(port_name, virtual=True) as port:
            tick_count = 0
            beat_count = 1  # 1-indexed: beat 1 is the first beat
            last_beat_time = time.time()
            current_bpm = 120.0
            last_ui_update = 0
            pending_reset = False  # Quantized reset - triggers on next beat

            # Initial draw
            draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

            while engine_state.running:
                # Check for keyboard input
                key = keyboard.get_key()
                if key:
                    if key == "q":
                        engine_state.running = False
                        break

                    # Pattern selection (1-9)
                    elif key in "123456789":
                        idx = int(key) - 1
                        if pattern_engine.set_pattern_by_index(idx):
                            ui_message = ""
                            draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Previous/Next pattern
                    elif key == "[":
                        pattern_engine.prev_pattern()
                        ui_message = ""
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)
                    elif key == "]":
                        pattern_engine.next_pattern()
                        ui_message = ""
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Spacebar: Send MIDI note (for Ableton MIDI mapping) and reset beat counter
                    elif key == " ":
                        # Send note C4 (note 60) on channel 0 - MIDI map this to Ableton's play/restart
                        midi_out.send(mido.Message("note_on", note=60, velocity=127, channel=0))
                        midi_out.send(mido.Message("note_off", note=60, velocity=0, channel=0))
                        # Reset our beat tracking to beat 1
                        tick_count = 0
                        beat_count = 1
                        ui_bar = 1
                        ui_beat = 1
                        last_beat_time = time.time()
                        with engine_state.lock:
                            engine_state.beat_position = 0.0
                            engine_state.beat_count = 1
                        ui_message = "SYNC → Bar 1"
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Blackout toggle (moved to 'b')
                    elif key == "b":
                        is_blackout = pattern_engine.toggle_blackout()
                        ui_message = "BLACKOUT" if is_blackout else ""
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Flash
                    elif key == "f":
                        pattern_engine.trigger_quick_action(QuickAction.flash(duration_beats=0.5))
                        ui_message = "FLASH!"
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Reset beat position (quantized to next beat)
                    elif key == "r":
                        pending_reset = True
                        ui_message = "Reset on next beat..."
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Reload patterns from disk
                    elif key == "R":
                        try:
                            count = pattern_engine.reload_strudel_patterns()
                            ui_message = f"Reloaded {count} patterns"
                        except Exception as e:
                            ui_message = f"Reload error: {e}"
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Pattern selector
                    elif key == "p":
                        pattern_selector_input(pattern_engine, keyboard)
                        ui_message = ""
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                # Non-blocking receive with timeout
                msg = port.receive(block=True)

                if msg is None:
                    continue

                if msg.type == "clock":
                    tick_count += 1
                    if tick_count >= TICKS_PER_BEAT:
                        tick_count = 0
                        beat_count += 1
                        now = time.time()

                        # Handle quantized reset
                        if pending_reset:
                            pending_reset = False
                            tick_count = 0
                            beat_count = 1  # Reset to beat 1
                            ui_bar = 1
                            ui_beat = 1
                            with engine_state.lock:
                                engine_state.beat_position = 0.0
                                engine_state.beat_count = 1
                            ui_message = "SYNCED!"
                            last_beat_time = now
                            draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)
                            continue

                        # Calculate BPM from beat timing
                        beat_duration = now - last_beat_time
                        if beat_duration > 0 and last_beat_time > 0:
                            current_bpm = 60.0 / beat_duration
                        last_beat_time = now

                        # Update UI state
                        ui_beat = ((beat_count - 1) % 4) + 1
                        ui_bar = (beat_count - 1) // 4 + 1
                        ui_bpm = current_bpm
                        ui_message = ""

                        # Redraw on each beat
                        draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                    # Calculate beat_position (0-indexed: beat 1 starts at 0.0)
                    beat_position = (beat_count - 1) + tick_count / TICKS_PER_BEAT

                    # Update shared state
                    with engine_state.lock:
                        engine_state.beat_position = beat_position
                        engine_state.bpm = current_bpm
                        engine_state.beat_count = beat_count

                elif msg.type == "start":
                    tick_count = 0
                    beat_count = 1  # Start at beat 1
                    last_beat_time = time.time()
                    ui_bar = 1
                    ui_beat = 1
                    ui_message = "MIDI Start"
                    with engine_state.lock:
                        engine_state.beat_position = 0.0
                        engine_state.beat_count = 1
                    draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                elif msg.type == "stop":
                    ui_message = "MIDI Stop"
                    draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                elif msg.type == "continue":
                    tick_count = 0
                    beat_count = 1  # Reset to beat 1
                    last_beat_time = time.time()
                    ui_bar = 1
                    ui_beat = 1
                    ui_message = "MIDI Continue"
                    with engine_state.lock:
                        engine_state.beat_position = 0.0
                        engine_state.beat_count = 1
                    draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

                elif msg.type == "songpos":
                    # Song position is in "MIDI beats" (16th notes), 4 per quarter note
                    position = msg.pos
                    beat_count = position // 4 + 1  # 1-indexed
                    tick_count = (position % 4) * (TICKS_PER_BEAT // 4)
                    ui_beat = ((beat_count - 1) % 4) + 1
                    ui_bar = (beat_count - 1) // 4 + 1
                    ui_message = f"Position: Bar {ui_bar} Beat {ui_beat}"
                    with engine_state.lock:
                        engine_state.beat_count = beat_count
                        engine_state.beat_position = (beat_count - 1) + tick_count / TICKS_PER_BEAT
                    draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(SHOW_CURSOR, end="", flush=True)
        engine_state.running = False
        keyboard.stop()
        if loader:
            loader.stop_watching()
        render_thread.join(timeout=1.0)
        # Close MIDI output port
        try:
            midi_out.close()
        except Exception:
            pass
        print("\n[SHUTDOWN] Stopping Hue streaming...")
        hue.stop()
        print("[SHUTDOWN] Done")


if __name__ == "__main__":
    main()
