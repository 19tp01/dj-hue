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

from dj_hue.patterns import PatternEngine, PatternLoader, LightSetup, QuickAction, ColorPalette


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
        self._channel_map = {}

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

        self._channel_map = {}
        for i, channel in enumerate(target_config.channels):
            for member in channel.members:
                light_id = member.service.rid
                self._channel_map[light_id] = i

        self._streaming = Streaming(self._bridge, target_config, ent_conf_repo)
        self._streaming.set_color_space("rgb")
        self._streaming.start_stream()
        self._running = True

        print(f"[HUE] Streaming to {len(self._channel_map)} lights")

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
        return len(self._channel_map)


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
            except Exception as e:
                print(f"\n[RENDER] Send error: {e}")
        streaming_service._last_message = message

        frame_count += 1

        # Report every 5 seconds
        now = time.time()
        if now - last_report >= 5.0:
            pattern = pattern_engine.current_pattern
            pattern_name = pattern.name if pattern else "None"
            print(f"\n[RENDER] frames={frame_count} | Pattern: {pattern_name}")
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
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")

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


def print_help(pattern_engine: PatternEngine):
    """Print control help."""
    print("\n" + "=" * 60)
    print("PATTERNS (press 1-9 to select):")
    for i, name in enumerate(pattern_engine.pattern_names[:9]):
        pattern = pattern_engine.get_pattern(name)
        marker = ">" if pattern == pattern_engine.current_pattern else " "
        key = i + 1
        print(f"  {marker} {key}: {pattern.name if pattern else name}")
    print("\nCONTROLS:")
    print("  1-9    = Quick select pattern (first 9)")
    print("  p      = Open pattern selector (all patterns)")
    print("  [/]    = Previous/Next pattern")
    print("  Space  = Toggle blackout")
    print("  f      = Flash (white)")
    print("  r      = Reset beat position")
    print("  h      = Show this help")
    print("  q      = Quit")
    print("=" * 60 + "\n")


def print_pattern_selector(pattern_engine: PatternEngine) -> None:
    """Print pattern selection menu with all available patterns."""
    patterns = pattern_engine.pattern_names
    current = pattern_engine.current_pattern

    print("\n" + "=" * 60)
    print("  PATTERN SELECTOR")
    print("  Type number and press Enter, or press Escape to cancel")
    print("=" * 60)

    for i, name in enumerate(patterns):
        pattern = pattern_engine.get_pattern(name)
        marker = ">" if pattern == current else " "
        palette_name = pattern.default_palette.name if pattern else "?"
        print(f"  {marker} {i + 1:2d}. {pattern.name if pattern else name} [{palette_name}]")

    print("=" * 60)
    print()


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

    # Initialize pattern engine
    num_lights = hue.light_count
    light_setup = LightSetup.create_default(num_lights)
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
    print(f"[MIDI] Creating virtual port: {port_name}")
    print("[MIDI] In Ableton: Preferences -> Link, Tempo & MIDI")
    print("[MIDI]   - Enable 'Sync' output for 'DJ-Hue Clock'")
    print()

    print_help(pattern_engine)

    keyboard = KeyboardListener()

    def signal_handler(sig, frame):
        engine_state.running = False
        print("\n[SHUTDOWN] Stopping...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        keyboard.start()

        with mido.open_input(port_name, virtual=True) as port:
            tick_count = 0
            beat_count = 0
            last_beat_time = time.time()
            current_bpm = 120.0

            print(f"[MIDI] Listening on '{port_name}'...")
            print("[MIDI] Waiting for MIDI Clock from Ableton...")
            print()

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
                            pattern = pattern_engine.current_pattern
                            print(f"\n>>> Pattern: {pattern.name}")

                    # Previous/Next pattern
                    elif key == "[":
                        pattern = pattern_engine.prev_pattern()
                        if pattern:
                            print(f"\n<<< Pattern: {pattern.name}")
                    elif key == "]":
                        pattern = pattern_engine.next_pattern()
                        if pattern:
                            print(f"\n>>> Pattern: {pattern.name}")

                    # Blackout toggle
                    elif key == " ":
                        is_blackout = pattern_engine.toggle_blackout()
                        print(f"\n{'[BLACKOUT]' if is_blackout else '[LIGHTS ON]'}")

                    # Flash
                    elif key == "f":
                        pattern_engine.trigger_quick_action(QuickAction.flash(duration_beats=0.5))
                        print("\n[FLASH!]")

                    # Reset beat position
                    elif key == "r":
                        tick_count = 0
                        beat_count = 0
                        with engine_state.lock:
                            engine_state.beat_position = 0.0
                            engine_state.beat_count = 0
                        print("\n[Beat position reset]")

                    # Help
                    elif key == "h":
                        print_help(pattern_engine)

                    # Pattern selector
                    elif key == "p":
                        pattern_selector_input(pattern_engine, keyboard)

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

                        # Calculate BPM from beat timing
                        beat_duration = now - last_beat_time
                        if beat_duration > 0 and last_beat_time > 0:
                            current_bpm = 60.0 / beat_duration
                        last_beat_time = now

                        # Beat position in bar (1-4)
                        beat_in_bar = ((beat_count - 1) % 4) + 1
                        bar = (beat_count - 1) // 4 + 1

                        # Print beat info
                        pattern = pattern_engine.current_pattern
                        pattern_name = pattern.name if pattern else "None"
                        print(
                            f"\r[BEAT] Bar {bar} Beat {beat_in_bar} | "
                            f"{current_bpm:.1f} BPM | Pattern: {pattern_name}        ",
                            end="",
                            flush=True,
                        )

                    # Calculate beat_position
                    beat_position = beat_count + tick_count / TICKS_PER_BEAT

                    # Update shared state
                    with engine_state.lock:
                        engine_state.beat_position = beat_position
                        engine_state.bpm = current_bpm
                        engine_state.beat_count = beat_count

                elif msg.type == "start":
                    print("\n[MIDI] Start received - resetting to beat 1")
                    tick_count = 0
                    beat_count = 0
                    last_beat_time = 0
                    with engine_state.lock:
                        engine_state.beat_position = 0.0
                        engine_state.beat_count = 0

                elif msg.type == "stop":
                    print("\n[MIDI] Stop received")

                elif msg.type == "continue":
                    print("\n[MIDI] Continue received - resetting to beat 1")
                    tick_count = 0
                    beat_count = 1
                    last_beat_time = time.time()
                    with engine_state.lock:
                        engine_state.beat_position = 1.0
                        engine_state.beat_count = 1

                elif msg.type == "songpos":
                    position = msg.pos
                    beat_count = position // 4
                    with engine_state.lock:
                        engine_state.beat_count = beat_count
                    print(f"\n[MIDI] Position: beat {beat_count}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        engine_state.running = False
        keyboard.stop()
        if loader:
            loader.stop_watching()
        render_thread.join(timeout=1.0)
        print("\n[SHUTDOWN] Stopping Hue streaming...")
        hue.stop()
        print("[SHUTDOWN] Done")


if __name__ == "__main__":
    main()
