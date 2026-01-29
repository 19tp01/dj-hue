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

from dj_hue.patterns import PatternEngine, LightSetup, LightGroup, QuickAction
from dj_hue.control.server import ControlServer


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
        light_order: list[str] | None = None,
    ):
        self.bridge_ip = bridge_ip
        self.username = username
        self.clientkey = clientkey
        self.entertainment_area_id = entertainment_area_id
        self.light_order = light_order or []  # List of light names/IDs in desired order

        self._streaming = None
        self._bridge = None
        self._entertainment = None
        self._running = False
        self._lock = threading.Lock()
        self._num_channels = 0
        self._light_groups: dict[str, list[int]] = {}  # Group name -> channel indices
        self._channel_to_api_channel: dict[int, int] = {}  # Our index -> API channel index
        self._light_info: list[dict] = []  # Light info for settings UI

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
        num_api_channels = len(target_config.channels)

        # Build light name/ID lookup for matching against light_order config
        light_names, rid_to_device = get_light_names(self.bridge_ip, self.username)

        # Build list of (api_channel_index, light_name, light_rid, device_id) for ordering
        api_channels_info = []
        rid_to_api_channels: dict[str, list[int]] = {}
        for api_idx, channel in enumerate(target_config.channels):
            for member in channel.members:
                rid = member.service.rid
                name = light_names.get(rid, "Unknown")
                device_id = rid_to_device.get(rid, rid)  # Fall back to RID if no device
                api_channels_info.append((api_idx, name, rid, device_id))
                if rid not in rid_to_api_channels:
                    rid_to_api_channels[rid] = []
                rid_to_api_channels[rid].append(api_idx)

        # Apply light_order if configured
        if self.light_order:
            # Build mapping from configured order to API channels
            ordered_api_channels = []
            used_api_channels = set()

            for order_entry in self.light_order:
                # Find matching API channel(s) by name or ID
                found = False
                for api_idx, name, rid, device_id in api_channels_info:
                    if api_idx in used_api_channels:
                        continue
                    if order_entry == name or order_entry == rid:
                        ordered_api_channels.append(api_idx)
                        used_api_channels.add(api_idx)
                        found = True
                        break

                if not found:
                    print(f"[HUE] Warning: light_order entry '{order_entry}' not found in entertainment area")

            # Add any remaining channels not in light_order at the end
            for api_idx, name, rid, device_id in api_channels_info:
                if api_idx not in used_api_channels:
                    ordered_api_channels.append(api_idx)
                    print(f"[HUE] Warning: light '{name}' not in light_order, appending at end")

            # Build our index -> API channel mapping
            self._channel_to_api_channel = {
                our_idx: api_idx for our_idx, api_idx in enumerate(ordered_api_channels)
            }
            self._num_channels = len(ordered_api_channels)
            print(f"[HUE] Applied custom light_order: {len(self.light_order)} lights configured")
        else:
            # Default: use API order directly
            self._channel_to_api_channel = {i: i for i in range(num_api_channels)}
            self._num_channels = num_api_channels

        # Now build groups using OUR indices (after reordering)
        # Group by DEVICE ID (not entertainment RID) to detect multi-segment lights
        device_to_our_channels: dict[str, list[int]] = {}
        for our_idx in range(self._num_channels):
            api_idx = self._channel_to_api_channel[our_idx]
            # Find device ID for this API channel
            for a_idx, name, rid, device_id in api_channels_info:
                if a_idx == api_idx:
                    if device_id not in device_to_our_channels:
                        device_to_our_channels[device_id] = []
                    device_to_our_channels[device_id].append(our_idx)
                    break

        # Build groups: "strip" for multi-segment devices, "lamps" for single-segment
        strip_channels = []
        lamp_channels = []
        for device_id, channels in device_to_our_channels.items():
            if len(channels) > 1:
                # Multi-segment device (like OmniGlow strip)
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

        # Build light info for settings UI
        self._light_info = []
        for our_idx in range(self._num_channels):
            api_idx = self._channel_to_api_channel[our_idx]
            # Find info for this API channel
            for a_idx, name, rid, device_id in api_channels_info:
                if a_idx == api_idx:
                    # Determine which groups this light belongs to
                    groups = [
                        group_name
                        for group_name, indices in self._light_groups.items()
                        if our_idx in indices
                    ]
                    self._light_info.append({
                        "rid": rid,
                        "name": name,
                        "index": our_idx,
                        "api_channel": api_idx,
                        "groups": sorted(groups),
                    })
                    break

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

    @property
    def channel_mapping(self) -> dict[int, int]:
        """Get our channel index -> API channel index mapping."""
        return self._channel_to_api_channel

    def get_light_info(self) -> list[dict]:
        """Get light info for settings UI.

        Returns list of dicts with:
            rid: Hue resource ID
            name: Light name from Hue API
            index: Our channel index (after reordering)
            api_channel: Original API channel index
            groups: List of group names this light belongs to
        """
        return self._light_info


class EngineState:
    """Thread-safe shared state between MIDI and render threads."""

    def __init__(self):
        self.lock = threading.Lock()
        self.beat_position = 0.0
        self.bpm = 120.0
        self.beat_count = 0
        self.running = True
        # Light identification (for settings UI)
        self.identify_light_index: int | None = None
        self.identify_until: float = 0.0  # time.time() when to stop
        # Per-zone brightness (0.0-1.0)
        self.zone_brightness: dict[str, float] = {
            "ceiling": 1.0,
            "perimeter": 1.0,
            "ambient": 1.0,
        }
        # Fade out state
        self.fade_active: bool = False
        self.fade_start_time: float = 0.0
        self.fade_duration: float = 2.0  # seconds
        # Pattern queue state
        self.queue_mode: int = 0  # 0=OFF, 1=1bar, 2=2bars
        self.queued_pattern_index: int | None = None
        self.queue_target_bar: int | None = None


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
    engine_state: EngineState,
    streaming,  # Direct Streaming object from hue-entertainment-pykit
    pattern_engine: PatternEngine,
    num_lights: int,
    channel_mapping: dict[int, int] | None = None,
    light_zones: dict[int, str] | None = None,
):
    """Dedicated thread for smooth Hue updates at fixed rate.

    Sends ALL lights in a SINGLE batched DTLS message for minimal latency.

    Args:
        channel_mapping: Maps our index (0..N) -> API channel index.
                        If None, assumes identity mapping.
        light_zones: Maps light index -> zone name (e.g., "ceiling", "perimeter").
                    Used for per-zone brightness control.
    """
    if channel_mapping is None:
        channel_mapping = {i: i for i in range(num_lights)}
    if light_zones is None:
        light_zones = {}

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

    # Diagnostic tracking
    send_errors = 0
    long_frames = 0
    last_light_state = None  # Track (r,g,b) of light 0 for state change detection
    state_stuck_start = None  # When current state started
    last_beat_pos = 0.0
    beat_stuck_count = 0
    LOG_DIAGNOSTICS = os.environ.get("DJ_HUE_DEBUG", "").lower() in ("1", "true", "yes")

    while engine_state.running:
        frame_start = time.time()

        # Detect if previous frame took too long (gap > 50ms suggests something stalled)
        frame_gap = frame_start - last_frame_end
        if frame_gap > 0.05 and frame_count > 0:  # > 50ms gap
            long_frames += 1
            if LOG_DIAGNOSTICS:
                print(f"[RENDER] WARNING: {frame_gap*1000:.0f}ms gap between frames!")

        # Get beat state
        with engine_state.lock:
            beat_pos = engine_state.beat_position
            bpm = engine_state.bpm

        # Check if beat position is stuck (not advancing)
        if beat_pos == last_beat_pos:
            beat_stuck_count += 1
            if beat_stuck_count == 50 and LOG_DIAGNOSTICS:  # ~1 second at 50Hz
                print(f"[RENDER] WARNING: beat_position stuck at {beat_pos:.3f} for 50+ frames!")
        else:
            if beat_stuck_count >= 50 and LOG_DIAGNOSTICS:
                print(f"[RENDER] beat_position unstuck, was stuck for {beat_stuck_count} frames")
            beat_stuck_count = 0
            last_beat_pos = beat_pos

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

        # Get zone brightness, fade state, and identify mode
        with engine_state.lock:
            zone_brightness = dict(engine_state.zone_brightness)
            identify_idx = engine_state.identify_light_index
            identify_until = engine_state.identify_until
            fade_active = engine_state.fade_active
            fade_start = engine_state.fade_start_time
            fade_duration = engine_state.fade_duration

        # Apply per-zone brightness multipliers
        for i, (r, g, b) in enumerate(light_colors):
            zone = light_zones.get(i)
            if zone and zone in zone_brightness:
                brightness = zone_brightness[zone]
                if brightness < 1.0:
                    light_colors[i] = (r * brightness, g * brightness, b * brightness)

        # Apply fade out multiplier
        if fade_active:
            elapsed = time.time() - fade_start
            if elapsed >= fade_duration:
                fade_mult = 0.0
            else:
                fade_mult = 1.0 - (elapsed / fade_duration)
            if fade_mult < 1.0:
                light_colors = [(r * fade_mult, g * fade_mult, b * fade_mult) for r, g, b in light_colors]

        if identify_idx is not None and 0 <= identify_idx < num_lights:
            now = time.time()
            if now < identify_until:
                # Flash pattern: alternate white/off every 150ms
                phase = int((identify_until - now) / 0.15) % 2
                if phase == 0:
                    light_colors[identify_idx] = (1.0, 1.0, 1.0)  # White
                else:
                    light_colors[identify_idx] = (0.0, 0.0, 0.0)  # Off
            else:
                # Done identifying, clear the flag
                with engine_state.lock:
                    engine_state.identify_light_index = None

        # Track state changes for diagnostics
        current_light_state = light_colors[0] if light_colors else (0, 0, 0)
        if current_light_state != last_light_state:
            if LOG_DIAGNOSTICS and state_stuck_start is not None:
                stuck_duration = frame_start - state_stuck_start
                is_on = current_light_state[0] > 0.01 or current_light_state[1] > 0.01 or current_light_state[2] > 0.01
                was_on = last_light_state and (last_light_state[0] > 0.01 or last_light_state[1] > 0.01 or last_light_state[2] > 0.01)
                transition = f"{'ON' if was_on else 'OFF'}->{'ON' if is_on else 'OFF'}"
                # Log ALL state changes to see if we're missing some
                print(f"[RENDER] {stuck_duration*1000:6.1f}ms @ beat {beat_pos:.4f} ({transition})")
            state_stuck_start = frame_start
            last_light_state = current_light_state

        # Send ALL lights in a single batched message for synchronized updates
        all_channels_data = b""
        for our_idx, (r, g, b) in enumerate(light_colors):
            api_channel = channel_mapping.get(our_idx, our_idx)
            r16, g16, b16 = rgb_to_rgb16(r, g, b)
            all_channels_data += struct.pack(">B", api_channel) + struct.pack(">HHH", r16, g16, b16)
        message = header + all_channels_data
        try:
            send_start = time.time()
            dtls_socket.send(message)
            send_elapsed = time.time() - send_start
            if send_elapsed > 0.05 and LOG_DIAGNOSTICS:  # > 50ms send time
                print(f"[RENDER] SLOW SEND: {send_elapsed*1000:.0f}ms")
        except Exception as e:
            send_errors += 1
            if LOG_DIAGNOSTICS:
                print(f"[RENDER] DTLS send error #{send_errors}: {e}")
        streaming_service._last_message = message

        frame_count += 1

        # Periodic stats report
        now = time.time()
        if now - last_report >= 5.0:
            if LOG_DIAGNOSTICS or send_errors > 0 or long_frames > 0:
                print(f"[RENDER] 5s stats: {frame_count} frames, {send_errors} errs, {long_frames} long, beat={beat_pos:.2f}")
            frame_count = 0
            send_errors = 0
            long_frames = 0
            last_report = now

        # Precise timing
        elapsed = time.time() - frame_start
        sleep_time = RENDER_INTERVAL - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
        elif LOG_DIAGNOSTICS and elapsed > RENDER_INTERVAL * 1.5:
            print(f"[RENDER] Frame overrun: {elapsed*1000:.1f}ms (target {RENDER_INTERVAL*1000:.1f}ms)")

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


def get_light_names(bridge_ip: str, username: str) -> tuple[dict[str, str], dict[str, str]]:
    """Fetch resource ID -> name and resource ID -> device ID mappings from bridge.

    Returns:
        (names, device_ids) where:
        - names: Maps light/entertainment IDs to human-readable names
        - device_ids: Maps entertainment IDs to their owner device IDs (for grouping)
    """
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    headers = {"hue-application-key": username}
    names: dict[str, str] = {}
    device_ids: dict[str, str] = {}

    try:
        # First, get device names (devices own both lights and entertainment resources)
        device_names: dict[str, str] = {}
        resp = requests.get(
            f"https://{bridge_ip}/clip/v2/resource/device",
            headers=headers, verify=False, timeout=5
        )
        for item in resp.json().get("data", []):
            device_names[item["id"]] = item.get("metadata", {}).get("name", "Unknown")

        # Map light IDs to names
        resp = requests.get(
            f"https://{bridge_ip}/clip/v2/resource/light",
            headers=headers, verify=False, timeout=5
        )
        for item in resp.json().get("data", []):
            # Light has its own name in metadata
            name = item.get("metadata", {}).get("name")
            if not name:
                # Fall back to owner device name
                owner = item.get("owner", {})
                name = device_names.get(owner.get("rid"), "Unknown")
            names[item["id"]] = name

        # Map entertainment IDs to names and device IDs
        resp = requests.get(
            f"https://{bridge_ip}/clip/v2/resource/entertainment",
            headers=headers, verify=False, timeout=5
        )
        for item in resp.json().get("data", []):
            owner = item.get("owner", {})
            owner_rid = owner.get("rid", "")
            name = device_names.get(owner_rid, "Unknown")
            names[item["id"]] = name
            device_ids[item["id"]] = owner_rid

    except Exception as e:
        print(f"[HUE] Warning: Could not fetch light names: {e}")

    return names, device_ids


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


def rgb_swatch(r: int, g: int, b: int) -> str:
    """Return 2-char colored block using 24-bit ANSI."""
    return f"\033[48;2;{r};{g};{b}m  \033[0m"


def hsv_to_rgb_int(hsv) -> tuple[int, int, int]:
    """Convert HSV to RGB integers (0-255)."""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(hsv.hue, hsv.saturation, hsv.value)
    return int(r * 255), int(g * 255), int(b * 255)


def palette_swatches(palette_name: str) -> str:
    """Generate color swatches for a palette."""
    from dj_hue.patterns.strudel.palettes import get_palette
    palette = get_palette(palette_name)
    if not palette:
        return ""
    swatches = ""
    for hsv in palette.colors:
        r, g, b = hsv_to_rgb_int(hsv)
        swatches += rgb_swatch(r, g, b)
    return swatches


def get_pattern_display_name(pattern_engine: PatternEngine, name: str) -> str:
    """Get display name for a pattern."""
    # All patterns are now Strudel LightPatterns, just return the name
    return name


def draw_interface(pattern_engine: PatternEngine, bpm: float, bar: int, beat: int, message: str = ""):
    """Draw the static interface."""
    current_name = pattern_engine.get_current_pattern_name()
    current_desc = pattern_engine.get_current_pattern_description()
    current_palette = pattern_engine.get_active_palette_name() or "Default"
    override = pattern_engine.get_palette_override()

    # Build the interface
    lines = []
    lines.append(f"{BOLD}DJ-HUE{RESET} │ {bpm:.0f} BPM │ Bar {bar} Beat {beat}")
    lines.append("─" * 50)

    # Current pattern (highlighted)
    lines.append(f"{BOLD}Pattern:{RESET} {current_name}")
    if current_desc:
        lines.append(f"  {DIM}{current_desc}{RESET}")

    # Current palette with ANSI preview
    palette_indicator = " (override)" if override else ""
    swatches = palette_swatches(current_palette) if current_palette != "Default" else ""
    lines.append(f"{BOLD}Palette:{RESET} {current_palette}{palette_indicator} {swatches}")
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
    lines.append(f"{DIM}[Tab] palettes  [/] prev/next  [b] blackout  [f] flash  [p] all  [q] quit{RESET}")

    # Message line
    if message:
        lines.append("")
        lines.append(f"  {message}")

    # Clear and draw
    output = CURSOR_HOME + CLEAR_SCREEN
    output += "\n".join(lines)
    print(output, flush=True)


def draw_palette_interface(pattern_engine: PatternEngine, bpm: float, bar: int, beat: int, message: str = ""):
    """Draw the palette selection interface."""
    current_pattern = pattern_engine.get_current_pattern_name()
    current_desc = pattern_engine.get_current_pattern_description()
    current_palette = pattern_engine.get_active_palette_name() or "Default"
    palette_info = pattern_engine.get_available_palettes()
    palettes = [p["name"] if isinstance(p, dict) else p for p in palette_info]
    override = pattern_engine.get_palette_override()

    lines = []
    lines.append(f"{BOLD}DJ-HUE{RESET} │ {bpm:.0f} BPM │ Bar {bar} Beat {beat}")
    lines.append("─" * 50)

    # Current pattern and palette with ANSI preview
    palette_indicator = " (override)" if override else ""
    swatches = palette_swatches(current_palette) if current_palette != "Default" else ""
    lines.append(f"{BOLD}Pattern:{RESET} {current_pattern}")
    if current_desc:
        lines.append(f"  {DIM}{current_desc}{RESET}")
    lines.append(f"{BOLD}Palette:{RESET} {current_palette}{palette_indicator} {swatches}")
    lines.append("")

    # Palette list with swatches
    lines.append(f"{DIM}Palettes [0-9]:{RESET}                   {DIM}(Tab for patterns){RESET}")

    # Option 0: Default (clears override)
    is_default = override is None
    marker = "▶" if is_default else " "
    line = f"  {marker} 0: Default (pattern's choice)"
    if is_default:
        line = f"{BOLD}{line}{RESET}"
    lines.append(line)

    # Palettes 1-9
    for i, name in enumerate(palettes[:9]):
        is_current = (name == override)
        marker = "▶" if is_current else " "
        swatches = palette_swatches(name)
        line = f"  {marker} {i+1}: {name:<12} {swatches}"
        if is_current:
            line = f"{BOLD}  {marker} {i+1}: {name:<12}{RESET} {swatches}"
        lines.append(line)

    # More indicator
    if len(palettes) > 9:
        lines.append(f"  {DIM}... +{len(palettes) - 9} more (press c){RESET}")

    lines.append("")
    lines.append(f"{DIM}[Tab] patterns  [/] prev/next  [b] blackout  [f] flash  [c] all  [q] quit{RESET}")

    if message:
        lines.append("")
        lines.append(f"  {message}")

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
        marker = "▶" if i == current_idx else " "
        line = f"  {marker} {i + 1:2d}. {display_name}"
        if i == current_idx:
            line = f"{BOLD}  {marker} {i + 1:2d}. {display_name}{RESET}"
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
                        name = pattern_engine.get_current_pattern_name()
                        print(f"\n>>> Selected: {name}")
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


def print_palette_selector(pattern_engine: PatternEngine) -> None:
    """Print palette selection menu with all palettes."""
    palette_info = pattern_engine.get_available_palettes()
    palettes = [p["name"] if isinstance(p, dict) else p for p in palette_info]
    override = pattern_engine.get_palette_override()

    output = CURSOR_HOME + CLEAR_SCREEN
    lines = []
    lines.append(f"{BOLD}PALETTE SELECTOR{RESET}")
    lines.append("─" * 50)
    lines.append(f"{DIM}Type number + Enter, or Escape to cancel{RESET}")
    lines.append("")

    # Option 0: Default
    is_default = override is None
    marker = "▶" if is_default else " "
    line = f"  {marker}  0. Default (pattern's choice)"
    if is_default:
        line = f"{BOLD}{line}{RESET}"
    lines.append(line)

    for i, name in enumerate(palettes):
        is_current = (name == override)
        marker = "▶" if is_current else " "
        swatches = palette_swatches(name)
        line = f"  {marker} {i+1:2d}. {name:<12} {swatches}"
        if is_current:
            line = f"{BOLD}  {marker} {i+1:2d}. {name:<12}{RESET} {swatches}"
        lines.append(line)

    lines.append("")
    lines.append("─" * 50)
    print(output + "\n".join(lines), flush=True)


def palette_selector_input(pattern_engine: PatternEngine, keyboard: "KeyboardListener") -> bool:
    """
    Handle palette selector input mode.

    Returns True if a palette was selected, False if cancelled.
    """
    print_palette_selector(pattern_engine)
    print("Enter palette number (0 for default): ", end="", flush=True)

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
                    idx = int(input_buffer)
                    if idx == 0:
                        pattern_engine.set_palette(None)  # Clear override
                        print("\n>>> Palette: Default")
                        return True
                    else:
                        palette_info = pattern_engine.get_available_palettes()
                        palettes = [p["name"] if isinstance(p, dict) else p for p in palette_info]
                        palette_idx = idx - 1
                        if 0 <= palette_idx < len(palettes):
                            pattern_engine.set_palette(palettes[palette_idx])
                            print(f"\n>>> Palette: {palettes[palette_idx]}")
                            return True
                        else:
                            print(f"\n[Invalid palette number: {input_buffer}]")
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


def main():
    """Main MIDI Clock to Hue with PatternEngine."""
    print("=" * 60)
    print("  MIDI Clock -> Hue Lights (Pattern Mode)")
    print("=" * 60)

    # Load config and start Hue
    hue_config = load_config()
    light_order = hue_config.get("light_order", [])
    custom_groups = hue_config.get("custom_groups", {})
    zone_config_yaml = hue_config.get("zones", {})
    hue = HueStreamer(
        bridge_ip=hue_config["bridge_ip"],
        username=hue_config["username"],
        clientkey=hue_config["clientkey"],
        entertainment_area_id=hue_config["entertainment_area_id"],
        light_order=light_order,
    )
    hue.start()

    # Initialize pattern engine with detected groups from Hue
    num_lights = hue.light_count
    light_setup = LightSetup(name="hue_auto", total_lights=num_lights)

    # Add detected groups (strip, lamps, etc.)
    for group_name, indices in hue.light_groups.items():
        light_setup.add_group(LightGroup(name=group_name, light_indices=indices))

    # Build light name to index mapping
    light_info = hue.get_light_info()
    name_to_idx = {info["name"]: info["index"] for info in light_info}

    # Add custom groups for pattern targeting (separate from zones)
    for group_name, light_names in custom_groups.items():
        group_indices = []
        for name in light_names:
            if name in name_to_idx:
                group_indices.append(name_to_idx[name])
            else:
                print(f"[GROUPS] Warning: light '{name}' not found for group '{group_name}'")
        if group_indices:
            light_setup.add_group(LightGroup(name=group_name, light_indices=group_indices))
            print(f"[GROUPS] Added custom group '{group_name}' with indices {group_indices}")

    # Build zone assignments from config (zones are mutually exclusive for brightness control)
    # Default: strip→ceiling, remaining lamps→perimeter
    ceiling_indices = list(hue.light_groups.get("strip", []))
    perimeter_indices = list(hue.light_groups.get("lamps", []))
    ambient_indices: list[int] = []

    # Process explicit zone assignments from config
    for zone_name, light_names in zone_config_yaml.items():
        for name in light_names:
            if name not in name_to_idx:
                print(f"[ZONES] Warning: light '{name}' not found for zone '{zone_name}'")
                continue
            idx = name_to_idx[name]
            # Remove from default zones (mutually exclusive)
            if idx in ceiling_indices:
                ceiling_indices.remove(idx)
            if idx in perimeter_indices:
                perimeter_indices.remove(idx)
            # Add to the specified zone
            if zone_name == "ambient":
                ambient_indices.append(idx)
            elif zone_name == "ceiling":
                ceiling_indices.append(idx)
            elif zone_name == "perimeter":
                perimeter_indices.append(idx)

    print(f"[ZONES] ceiling={ceiling_indices}, perimeter={perimeter_indices}, ambient={ambient_indices}")

    # Create ambient group for pattern targeting (seq() uses this)
    if ambient_indices:
        light_setup.add_group(LightGroup(name="ambient", light_indices=ambient_indices))

    # Build light_zones mapping (light index -> zone name)
    light_zones: dict[int, str] = {}
    for idx in ceiling_indices:
        light_zones[idx] = "ceiling"
    for idx in perimeter_indices:
        light_zones[idx] = "perimeter"
    for idx in ambient_indices:
        light_zones[idx] = "ambient"

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

    # Create pattern engine with user patterns directory
    # Patterns are auto-loaded via @pattern decorator
    patterns_dir = Path(__file__).parent.parent.parent.parent / "patterns"
    pattern_engine = PatternEngine(light_setup=light_setup, patterns_dir=patterns_dir)
    print(f"[PATTERNS] Loaded {len(pattern_engine.pattern_names)} patterns")

    # Shared state between MIDI and render threads
    engine_state = EngineState()

    # Start render thread
    render_thread = threading.Thread(
        target=render_loop,
        args=(engine_state, hue._streaming, pattern_engine, num_lights, hue.channel_mapping, light_zones),
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
    ui_mode = "pattern"  # "pattern" or "palette"

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

        # Start control server for touch UI
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
        control_server = ControlServer(
            pattern_engine=pattern_engine,
            engine_state=engine_state,
            midi_out=midi_out,
            hue_streamer=hue,
            config_path=config_path,
        )
        control_thread = control_server.start_in_thread()

        # Set up callback to cancel fade on pattern change
        def on_pattern_change(name: str):
            with engine_state.lock:
                if engine_state.fade_active:
                    engine_state.fade_active = False

        pattern_engine._on_pattern_change = on_pattern_change

        with mido.open_input(port_name, virtual=True) as port:
            tick_count = 0
            beat_count = 1  # 1-indexed: beat 1 is the first beat
            last_beat_time = time.time()
            current_bpm = 120.0
            last_ui_update = 0
            pending_reset = False  # Quantized reset - triggers on next beat

            # Helper to redraw based on current mode
            def redraw():
                if ui_mode == "pattern":
                    draw_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)
                else:
                    draw_palette_interface(pattern_engine, ui_bpm, ui_bar, ui_beat, ui_message)

            # Initial draw
            redraw()

            while engine_state.running:
                # Check for keyboard input
                key = keyboard.get_key()
                if key:
                    if key == "q":
                        engine_state.running = False
                        break

                    # Tab: toggle mode
                    elif key == "\t":
                        ui_mode = "palette" if ui_mode == "pattern" else "pattern"
                        ui_message = ""
                        redraw()

                    # Number selection (mode-dependent)
                    elif key == "0":
                        if ui_mode == "palette":
                            pattern_engine.set_palette(None)  # Clear override
                            ui_message = ""
                            redraw()

                    elif key in "123456789":
                        if ui_mode == "pattern":
                            # Pattern selection
                            idx = int(key) - 1
                            if pattern_engine.set_pattern_by_index(idx):
                                ui_message = ""
                                redraw()
                        else:
                            # Palette selection
                            idx = int(key) - 1
                            palette_info = pattern_engine.get_available_palettes()
                            palettes = [p["name"] if isinstance(p, dict) else p for p in palette_info]
                            if idx < len(palettes):
                                pattern_engine.set_palette(palettes[idx])
                                ui_message = ""
                                redraw()

                    # Previous/Next (mode-dependent)
                    elif key == "[":
                        if ui_mode == "pattern":
                            pattern_engine.prev_pattern()
                        else:
                            # Cycle through palettes (prev)
                            palette_info = pattern_engine.get_available_palettes()
                            palettes = [p["name"] if isinstance(p, dict) else p for p in palette_info]
                            override = pattern_engine.get_palette_override()
                            if override is None:
                                # From default, go to last palette
                                if palettes:
                                    pattern_engine.set_palette(palettes[-1])
                            else:
                                try:
                                    idx = palettes.index(override)
                                    if idx == 0:
                                        pattern_engine.set_palette(None)  # Back to default
                                    else:
                                        pattern_engine.set_palette(palettes[idx - 1])
                                except ValueError:
                                    pattern_engine.set_palette(None)
                        ui_message = ""
                        redraw()

                    elif key == "]":
                        if ui_mode == "pattern":
                            pattern_engine.next_pattern()
                        else:
                            # Cycle through palettes (next)
                            palette_info = pattern_engine.get_available_palettes()
                            palettes = [p["name"] if isinstance(p, dict) else p for p in palette_info]
                            override = pattern_engine.get_palette_override()
                            if override is None:
                                # From default, go to first palette
                                if palettes:
                                    pattern_engine.set_palette(palettes[0])
                            else:
                                try:
                                    idx = palettes.index(override)
                                    if idx >= len(palettes) - 1:
                                        pattern_engine.set_palette(None)  # Back to default
                                    else:
                                        pattern_engine.set_palette(palettes[idx + 1])
                                except ValueError:
                                    pattern_engine.set_palette(None)
                        ui_message = ""
                        redraw()

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
                        redraw()

                    # Period: Send MIDI note for tap tempo (for Ableton MIDI mapping)
                    elif key == ".":
                        # Send note C#4 (note 61) on channel 0 - MIDI map this to tap tempo
                        midi_out.send(mido.Message("note_on", note=61, velocity=127, channel=0))
                        midi_out.send(mido.Message("note_off", note=61, velocity=0, channel=0))
                        ui_message = "TAP"
                        redraw()

                    # Blackout toggle
                    elif key == "b":
                        is_blackout = pattern_engine.toggle_blackout()
                        ui_message = "BLACKOUT" if is_blackout else ""
                        redraw()

                    # Flash
                    elif key == "f":
                        pattern_engine.trigger_quick_action(QuickAction.flash(duration_beats=0.5))
                        ui_message = "FLASH!"
                        redraw()

                    # Reset beat position (quantized to next beat)
                    elif key == "r":
                        pending_reset = True
                        ui_message = "Reset on next beat..."
                        redraw()

                    # Reload patterns from disk
                    elif key == "R":
                        try:
                            count = pattern_engine.reload_strudel_patterns()
                            ui_message = f"Reloaded {count} patterns"
                        except Exception as e:
                            ui_message = f"Reload error: {e}"
                        redraw()

                    # Pattern selector (full list)
                    elif key == "p":
                        pattern_selector_input(pattern_engine, keyboard)
                        ui_message = ""
                        redraw()

                    # Palette selector (full list)
                    elif key == "c":
                        palette_selector_input(pattern_engine, keyboard)
                        ui_message = ""
                        redraw()

                # Receive with timeout so we can check for shutdown
                msg = port.poll()  # Non-blocking

                if msg is None:
                    time.sleep(0.001)  # Brief sleep when no MIDI to reduce CPU
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
                            redraw()
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

                        # Check for queued pattern trigger at bar boundary (beat 1)
                        if ui_beat == 1:
                            with engine_state.lock:
                                queued_idx = engine_state.queued_pattern_index
                                target_bar = engine_state.queue_target_bar
                            if queued_idx is not None and target_bar is not None:
                                if ui_bar >= target_bar:
                                    pattern_engine.set_pattern_by_index(queued_idx)
                                    with engine_state.lock:
                                        engine_state.queued_pattern_index = None
                                        engine_state.queue_target_bar = None
                                    ui_message = "Queued!"

                        # Redraw on each beat
                        redraw()

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
                    redraw()

                elif msg.type == "stop":
                    ui_message = "MIDI Stop"
                    redraw()

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
                    redraw()

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
                    redraw()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(SHOW_CURSOR, end="", flush=True)
        engine_state.running = False
        keyboard.stop()
        render_thread.join(timeout=1.0)
        # Stop control server
        try:
            control_server.stop()
            control_thread.join(timeout=1.0)
        except Exception:
            pass
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
