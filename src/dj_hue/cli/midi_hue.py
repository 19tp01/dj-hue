"""MIDI Clock to Hue lights - syncs to Ableton's Tempo Follower.

Uses MIDI Clock output from Ableton (works with Tempo Follower enabled).
Supports two modes: Flash (simple beat flash) and Effects (waveform-based LFOs).
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
from typing import Dict

import mido

from dj_hue.lights.effects import EffectsEngine

# Modes
MODE_FLASH = "flash"
MODE_EFFECTS = "effects"


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
        self._pending_states: Dict[int, LightState] = {}
        self._channel_map: Dict[str, int] = {}

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

    def set_all_lights(self, r: int, g: int, b: int) -> None:
        """Set all lights to the same color."""
        with self._lock:
            for channel_id in range(len(self._channel_map)):
                self._pending_states[channel_id] = LightState(
                    light_id=channel_id,
                    r=max(0, min(255, r)),
                    g=max(0, min(255, g)),
                    b=max(0, min(255, b)),
                )

    def set_light(self, channel_id: int, r: int, g: int, b: int) -> None:
        """Set a single light to a color."""
        with self._lock:
            self._pending_states[channel_id] = LightState(
                light_id=channel_id,
                r=max(0, min(255, r)),
                g=max(0, min(255, g)),
                b=max(0, min(255, b)),
            )

    def flush(self) -> None:
        """Send all pending color updates."""
        if not self._streaming or not self._running:
            return

        with self._lock:
            for key, state in self._pending_states.items():
                r_norm = state.r / 255.0
                g_norm = state.g / 255.0
                b_norm = state.b / 255.0
                channel_id = (
                    key if isinstance(key, int) else self._channel_map.get(key, 0)
                )

                try:
                    self._streaming.set_input((r_norm, g_norm, b_norm, channel_id))
                except Exception as e:
                    print(f"[HUE] Error: {e}")

            self._pending_states.clear()

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


# Color schemes
COLORS = [
    (255, 50, 0),  # Orange-red
    (255, 0, 150),  # Magenta
    (0, 100, 255),  # Blue
    (0, 255, 100),  # Green
    (255, 200, 0),  # Yellow
    (150, 0, 255),  # Purple
    (0, 255, 255),  # Cyan
    (255, 100, 100),  # Pink
]

# MIDI Clock sends 24 ticks per quarter note (beat)
TICKS_PER_BEAT = 24

# Anticipation: trigger lights this many ticks BEFORE the beat
# At 120 BPM: 24 ticks = 500ms, so 3 ticks ≈ 62ms early
# Adjust this value to compensate for Hue latency (try 2-5)
ANTICIPATION_TICKS = 6

# Render thread runs at 25 Hz to match Zigbee transmission rate
# Higher rates cause queue buildup in hue-entertainment-pykit
# Stream at 50 Hz - Philips recommends this to compensate for UDP packet loss
# The bridge only processes at 25 Hz, but the redundancy prevents dropped frames
RENDER_HZ = 50
RENDER_INTERVAL = 1.0 / RENDER_HZ


class BeatState:
    """Thread-safe shared state between MIDI and render threads."""

    def __init__(self):
        self.lock = threading.Lock()
        self.beat_position = 0.0
        self.bpm = 120.0
        self.beat_count = 0
        self.running = True
        # Mode state
        self.mode = MODE_FLASH
        self.unified_mode = True
        # Flash mode state
        self.flash_color = (20, 20, 20)  # Current color for flash mode
        self.flash_triggered = False


def rgb_to_rgb16(r: float, g: float, b: float, gamma: float = 2.2) -> tuple[int, int, int]:
    """Convert RGB floats (0.0-1.0) to RGB16 (0-65535) with gamma correction.

    Gamma correction makes fades perceptually linear. Without it, LED fades
    look like they rush through dark values and stall in bright values.
    """
    r = max(0.0, min(1.0, r)) ** gamma
    g = max(0.0, min(1.0, g)) ** gamma
    b = max(0.0, min(1.0, b)) ** gamma
    return (int(r * 65535), int(g * 65535), int(b * 65535))


def render_loop(
    beat_state: BeatState,
    streaming,  # Direct Streaming object from hue-entertainment-pykit
    effects_engine: EffectsEngine,
    num_lights: int,
):
    """Dedicated thread for smooth Hue updates at fixed rate.

    Sends ALL lights in a SINGLE batched DTLS message for minimal latency.
    Uses a socket lock to prevent interference from library's background threads.
    """
    print(f"[RENDER] Started at {RENDER_HZ} Hz (batched mode)")

    # Access internals for direct socket access
    streaming_service = streaming._streaming_service
    dtls_socket = streaming_service._dtls_service.get_socket()

    # IMPORTANT: Stop the library's background threads to prevent interference
    # They send on the same socket which could cause conflicts
    print("[RENDER] Stopping library's background threads...")
    streaming_service._is_connection_alive = False  # Signal threads to stop
    # Wait for them to finish (they check this flag in their loops)
    import time as time_module
    time_module.sleep(1.5)  # Give threads time to exit (queue timeout is 1 second)
    streaming_service._is_connection_alive = True  # Re-enable for our use
    print("[RENDER] Library threads stopped, we have exclusive socket access")

    # Debug: Print what the library's header looks like
    lib_header = (
        streaming_service._protocol_name
        + streaming_service._version
        + streaming_service._sequence_id
        + streaming_service._reserved
        + streaming_service._color_space
        + streaming_service._reserved2
        + streaming_service._entertainment_id
    )
    print(f"[DEBUG] Library header ({len(lib_header)} bytes): {lib_header.hex()}")

    # Pre-build the message header (same for all messages)
    protocol_name = "HueStream".encode("utf-8")
    version = struct.pack(">BB", 0x02, 0x00)
    sequence_id = struct.pack(">B", 0x07)
    reserved = b"\x00\x00"
    color_space = struct.pack(">B", 0x00)  # RGB
    reserved2 = b"\x00"
    entertainment_id = streaming_service._entertainment_config.id.encode("utf-8")

    header = protocol_name + version + sequence_id + reserved + color_space + reserved2 + entertainment_id
    print(f"[DEBUG] Our header ({len(header)} bytes): {header.hex()}")
    print(f"[DEBUG] Headers match: {header == lib_header}")

    # Timing diagnostics
    frame_count = 0
    last_report = time.time()
    last_frame_end = time.time()

    # Track gaps and slowdowns
    gap_count = 0
    max_gap = 0.0
    max_send = 0.0
    max_compute = 0.0
    max_lock = 0.0

    # Track RGB values to detect discontinuities
    last_rgb = None
    rgb_jumps = 0  # Count of large RGB changes between frames

    while beat_state.running:
        frame_start = time.time()

        # Check gap since last frame
        gap = (frame_start - last_frame_end) * 1000
        if gap > RENDER_INTERVAL * 1000 * 1.5:  # More than 50% over expected
            gap_count += 1
        max_gap = max(max_gap, gap)

        # Time lock acquisition
        lock_start = time.time()
        with beat_state.lock:
            mode = beat_state.mode
            unified = beat_state.unified_mode
            beat_pos = beat_state.beat_position
            bpm = beat_state.bpm
            flash_color = beat_state.flash_color
        lock_time = (time.time() - lock_start) * 1000
        max_lock = max(max_lock, lock_time)

        # Time computation
        compute_start = time.time()

        # Update effects engine outside the lock
        effects_engine.beat_clock.beat_position = beat_pos
        effects_engine.beat_clock.bpm = bpm

        # Compute colors for all lights
        if mode == MODE_EFFECTS:
            if unified:
                rgb = effects_engine.compute_unified_color()
                light_colors = [(rgb.r / 255.0, rgb.g / 255.0, rgb.b / 255.0)] * num_lights
            else:
                colors = effects_engine.compute_colors()
                light_colors = []
                for channel_id in range(num_lights):
                    rgb_val = colors.get(channel_id, effects_engine.compute_unified_color())
                    light_colors.append((rgb_val.r / 255.0, rgb_val.g / 255.0, rgb_val.b / 255.0))
        else:
            # Flash mode - same color for all
            light_colors = [(flash_color[0] / 255.0, flash_color[1] / 255.0, flash_color[2] / 255.0)] * num_lights

        compute_time = (time.time() - compute_start) * 1000
        max_compute = max(max_compute, compute_time)

        # Send ALL lights in a single batched message for synchronized updates
        send_start = time.time()
        all_channels_data = b""
        for channel_id, (r, g, b) in enumerate(light_colors):
            r16, g16, b16 = rgb_to_rgb16(r, g, b)
            all_channels_data += struct.pack(">B", channel_id) + struct.pack(">HHH", r16, g16, b16)
        message = header + all_channels_data
        try:
            dtls_socket.send(message)
        except Exception as e:
            print(f"\n[RENDER] Send error: {e}")
        streaming_service._last_message = message  # For library's keep-alive
        send_time = (time.time() - send_start) * 1000
        max_send = max(max_send, send_time)

        # Track RGB continuity - detect large jumps that would appear as flicker
        current_rgb = light_colors[0] if light_colors else (0, 0, 0)
        if last_rgb is not None:
            # Calculate max change in any channel
            max_change = max(
                abs(current_rgb[0] - last_rgb[0]),
                abs(current_rgb[1] - last_rgb[1]),
                abs(current_rgb[2] - last_rgb[2]),
            )
            # A jump > 0.3 (30% brightness change) in one frame would be noticeable
            if max_change > 0.3:
                rgb_jumps += 1
                print(f"\n[JUMP] RGB changed by {max_change:.2f}: {last_rgb} -> {current_rgb}")
        last_rgb = current_rgb

        frame_count += 1

        # Report every 5 seconds
        now = time.time()
        if now - last_report >= 5.0:
            print(f"\n[TIMING] frames={frame_count} gaps={gap_count} jumps={rgb_jumps} | max: gap={max_gap:.1f}ms lock={max_lock:.1f}ms compute={max_compute:.1f}ms send={max_send:.1f}ms")
            rgb_jumps = 0
            frame_count = 0
            gap_count = 0
            max_gap = 0.0
            max_send = 0.0
            max_compute = 0.0
            max_lock = 0.0
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


def main():
    """Main MIDI Clock to Hue loop."""
    print("=" * 50)
    print("  MIDI Clock -> Hue Lights")
    print("=" * 50)

    # Load config and start Hue
    hue_config = load_config()
    hue = HueStreamer(
        bridge_ip=hue_config["bridge_ip"],
        username=hue_config["username"],
        clientkey=hue_config["clientkey"],
        entertainment_area_id=hue_config["entertainment_area_id"],
    )
    hue.start()

    # Initialize effects engine
    num_lights = hue.light_count
    effects_engine = EffectsEngine(num_lights=num_lights)

    # Shared state between MIDI and render threads
    beat_state = BeatState()

    # Start render thread - pass streaming object directly for lower latency
    render_thread = threading.Thread(
        target=render_loop,
        args=(beat_state, hue._streaming, effects_engine, num_lights),
        daemon=True,
    )
    render_thread.start()

    # Create virtual MIDI port
    port_name = "DJ-Hue Clock"
    print(f"[MIDI] Creating virtual port: {port_name}")
    print("[MIDI] In Ableton: Preferences → Link, Tempo & MIDI")
    print("[MIDI]   - Enable 'Sync' output for 'DJ-Hue Clock'")
    print("[MIDI]   - Enable Tempo Follower")
    print()
    print("[KEYS] e=mode | u=unified | p=pattern | 1-9=select | q=quit")
    print()

    keyboard = KeyboardListener()

    def signal_handler(sig, frame):
        beat_state.running = False
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
            print(f"[MODE] {beat_state.mode.upper()}")
            print()

            while beat_state.running:
                # Check for keyboard input
                key = keyboard.get_key()
                if key:
                    if key == "q":
                        beat_state.running = False
                        break
                    elif key == "e":
                        # Toggle mode
                        with beat_state.lock:
                            beat_state.mode = (
                                MODE_EFFECTS if beat_state.mode == MODE_FLASH else MODE_FLASH
                            )
                            mode = beat_state.mode
                        print(f"\n[MODE] Switched to {mode.upper()}")
                        if mode == MODE_EFFECTS:
                            print(f"[PATTERN] {effects_engine.current_pattern_name}")
                    elif key == "u":
                        # Toggle unified mode
                        with beat_state.lock:
                            beat_state.unified_mode = not beat_state.unified_mode
                            unified = beat_state.unified_mode
                        mode_str = "ON (all same)" if unified else "OFF (per-light)"
                        print(f"\n[UNIFIED] {mode_str}")
                    elif key == "p" and beat_state.mode == MODE_EFFECTS:
                        # Next pattern
                        pattern_name = effects_engine.next_pattern()
                        print(f"\n[PATTERN] {pattern_name}")
                    elif key in "123456789" and beat_state.mode == MODE_EFFECTS:
                        # Select pattern by number
                        pattern_names = list(effects_engine.patterns.keys())
                        idx = int(key) - 1
                        if idx < len(pattern_names):
                            effects_engine.set_pattern(pattern_names[idx])
                            print(f"\n[PATTERN] {pattern_names[idx]}")

                # Non-blocking receive with timeout
                msg = port.receive(block=True)

                if msg is None:
                    continue

                if msg.type == "clock":
                    # First: advance tick_count and handle beat boundary
                    # This must happen BEFORE calculating beat_position to avoid
                    # a race condition where position briefly jumps backward
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
                        mode_str = (
                            f"{beat_state.mode.upper()}"
                            if beat_state.mode == MODE_FLASH
                            else f"{effects_engine.current_pattern_name}"
                        )
                        print(
                            f"\r[BEAT] Bar {bar} Beat {beat_in_bar} | "
                            f"{current_bpm:.1f} BPM | {mode_str}        ",
                            end="",
                            flush=True,
                        )

                    # Now calculate beat_position with consistent tick/beat values
                    beat_position = beat_count + tick_count / TICKS_PER_BEAT

                    # Update shared state (render thread reads this)
                    with beat_state.lock:
                        beat_state.beat_position = beat_position
                        beat_state.bpm = current_bpm
                        beat_state.beat_count = beat_count

                    # Flash mode: update color on beat (with anticipation)
                    if beat_state.mode == MODE_FLASH:
                        trigger_tick = TICKS_PER_BEAT - ANTICIPATION_TICKS
                        if tick_count == trigger_tick:
                            next_beat = beat_count + 1
                            bar = (next_beat - 1) // 4 + 1
                            color_idx = (bar - 1) % len(COLORS)
                            with beat_state.lock:
                                beat_state.flash_color = COLORS[color_idx]

                elif msg.type == "start":
                    print("\n[MIDI] Start received - resetting to beat 1")
                    tick_count = 0
                    beat_count = 0
                    last_beat_time = 0
                    with beat_state.lock:
                        beat_state.beat_position = 0.0
                        beat_state.beat_count = 0

                elif msg.type == "stop":
                    print("\n[MIDI] Stop received")
                    with beat_state.lock:
                        beat_state.flash_color = (20, 20, 20)

                elif msg.type == "continue":
                    print("\n[MIDI] Continue received")

                elif msg.type == "songpos":
                    position = msg.pos
                    beat_count = position // 4
                    with beat_state.lock:
                        beat_state.beat_count = beat_count
                    print(f"\n[MIDI] Position: beat {beat_count}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        beat_state.running = False
        keyboard.stop()
        render_thread.join(timeout=1.0)
        print("\n[SHUTDOWN] Stopping Hue streaming...")
        hue.stop()
        print("[SHUTDOWN] Done")


if __name__ == "__main__":
    main()
