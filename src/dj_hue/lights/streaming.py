"""Hue Entertainment API streaming."""

from dataclasses import dataclass
from typing import Optional
import threading


@dataclass
class LightState:
    """RGB state for a light."""
    light_id: int
    r: int  # 0-255
    g: int
    b: int


class HueStreamer:
    """
    Stream color updates to Hue lights via Entertainment API.

    Uses hue-entertainment-pykit for DTLS connection handling.
    """

    def __init__(
        self,
        bridge_ip: str,
        username: str,
        clientkey: str,
        entertainment_area_id: str,
        fps: int = 25,
    ):
        self.bridge_ip = bridge_ip
        self.username = username
        self.clientkey = clientkey
        self.entertainment_area_id = entertainment_area_id
        self.fps = fps
        self.frame_time = 1.0 / fps

        self._streaming = None
        self._bridge = None
        self._entertainment = None
        self._running = False
        self._lock = threading.Lock()
        self._pending_states: dict[int, LightState] = {}
        self._channel_map: dict[str, int] = {}  # light_id -> channel_id

    def start(self) -> None:
        """Start the streaming connection."""
        try:
            from hue_entertainment_pykit import Bridge, Entertainment, Streaming
        except ImportError:
            raise ImportError(
                "hue-entertainment-pykit is required. "
                "Install with: pip install hue-entertainment-pykit"
            )

        # Create bridge connection
        # hue_app_id is required for DTLS PSK identity (use username)
        self._bridge = Bridge(
            ip_address=self.bridge_ip,
            username=self.username,
            clientkey=self.clientkey,
            hue_app_id=self.username,
        )

        # Get entertainment configuration
        self._entertainment = Entertainment(self._bridge)
        ent_configs_dict = self._entertainment.get_entertainment_configs()
        ent_conf_repo = self._entertainment.get_ent_conf_repo()

        # Find our entertainment area
        target_config = None
        for config_id, config in ent_configs_dict.items():
            if config_id == self.entertainment_area_id or config.id == self.entertainment_area_id:
                target_config = config
                break

        if target_config is None:
            available = list(ent_configs_dict.keys())
            raise ValueError(
                f"Entertainment area '{self.entertainment_area_id}' not found. "
                f"Available: {available}"
            )

        # Build channel map
        self._channel_map = {}
        for i, channel in enumerate(target_config.channels):
            for member in channel.members:
                # member.service.rid is the light ID
                light_id = member.service.rid
                self._channel_map[light_id] = i

        # Start streaming
        self._streaming = Streaming(
            self._bridge,
            target_config,
            ent_conf_repo,
        )
        self._streaming.set_color_space("rgb")
        self._streaming.start_stream()
        self._running = True

        print(f"Streaming started to {len(self._channel_map)} lights")

    def set_light_color(
        self,
        light_id: str | int,
        r: int,
        g: int,
        b: int,
    ) -> None:
        """
        Queue a color update for a light.

        Args:
            light_id: Light ID (string UUID or channel index)
            r, g, b: Color values (0-255)
        """
        with self._lock:
            # Handle both string IDs and integer channel indices
            if isinstance(light_id, int):
                key = light_id
            else:
                key = light_id

            self._pending_states[key] = LightState(
                light_id=key if isinstance(key, int) else 0,
                r=max(0, min(255, r)),
                g=max(0, min(255, g)),
                b=max(0, min(255, b)),
            )

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

    def flush(self) -> None:
        """Send all pending color updates."""
        if not self._streaming or not self._running:
            return

        with self._lock:
            for key, state in self._pending_states.items():
                # Normalize to 0.0-1.0 range
                r_norm = state.r / 255.0
                g_norm = state.g / 255.0
                b_norm = state.b / 255.0

                # Determine channel index
                if isinstance(key, str):
                    channel_id = self._channel_map.get(key, 0)
                else:
                    channel_id = key

                # Set color on channel using set_input
                # set_input expects (r, g, b, channel_id) tuple for RGB mode
                try:
                    self._streaming.set_input((r_norm, g_norm, b_norm, channel_id))
                except Exception as e:
                    print(f"Error setting light {channel_id}: {e}")

            self._pending_states.clear()

    def stop(self) -> None:
        """Stop the streaming connection."""
        self._running = False

        if self._streaming:
            try:
                self._streaming.stop_stream()
            except Exception as e:
                print(f"Error stopping stream: {e}")
            self._streaming = None

        self._bridge = None
        self._entertainment = None

    @property
    def is_running(self) -> bool:
        """Check if streaming is active."""
        return self._running

    @property
    def light_count(self) -> int:
        """Get number of lights in entertainment area."""
        return len(self._channel_map)

    def get_channel_ids(self) -> list[int]:
        """Get list of channel IDs (0-indexed)."""
        return list(range(len(self._channel_map)))


class MockStreamer:
    """Mock streamer for testing without actual Hue bridge."""

    def __init__(self, num_lights: int = 6):
        self.num_lights = num_lights
        self._running = False
        self._states: dict[int, tuple[int, int, int]] = {}

    def start(self) -> None:
        """Start mock streaming."""
        self._running = True
        print(f"Mock streaming started with {self.num_lights} lights")

    def set_light_color(self, light_id: int, r: int, g: int, b: int) -> None:
        """Queue color update."""
        self._states[light_id] = (r, g, b)

    def set_all_lights(self, r: int, g: int, b: int) -> None:
        """Set all lights."""
        for i in range(self.num_lights):
            self._states[i] = (r, g, b)

    def flush(self) -> None:
        """Print current states (for debugging)."""
        if self._states:
            bars = []
            for i in range(self.num_lights):
                if i in self._states:
                    r, g, b = self._states[i]
                    # Simple brightness bar
                    brightness = (r + g + b) / (3 * 255)
                    bar_len = int(brightness * 10)
                    bars.append(f"L{i}:{'█' * bar_len}{'░' * (10 - bar_len)}")
            if bars:
                print(" ".join(bars), end="\r")

    def stop(self) -> None:
        """Stop mock streaming."""
        self._running = False
        print("\nMock streaming stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def light_count(self) -> int:
        return self.num_lights

    def get_channel_ids(self) -> list[int]:
        return list(range(self.num_lights))
