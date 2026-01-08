"""Ableton Link to Hue lights - beat-synced light control.

Uses Ableton Link for rock-solid tempo sync instead of audio analysis.
"""

import asyncio
import os
import signal
import threading
import yaml
from dataclasses import dataclass
from typing import Dict

from aalink import Link


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
            if config_id == self.entertainment_area_id or config.id == self.entertainment_area_id:
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

    def flush(self) -> None:
        """Send all pending color updates."""
        if not self._streaming or not self._running:
            return

        with self._lock:
            for key, state in self._pending_states.items():
                r_norm = state.r / 255.0
                g_norm = state.g / 255.0
                b_norm = state.b / 255.0
                channel_id = key if isinstance(key, int) else self._channel_map.get(key, 0)

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
    (255, 50, 0),    # Orange-red
    (255, 0, 150),   # Magenta
    (0, 100, 255),   # Blue
    (0, 255, 100),   # Green
    (255, 200, 0),   # Yellow
    (150, 0, 255),   # Purple
    (0, 255, 255),   # Cyan
    (255, 100, 100), # Pink
]


def load_config():
    """Load Hue config from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config.yaml')

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config not found: {config_path}\n"
            "Run 'dj-hue --setup' first."
        )

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config.get('hue', {})


async def main():
    """Main Ableton Link to Hue loop."""
    print("=" * 50)
    print("  Ableton Link -> Hue Lights")
    print("=" * 50)

    # Load config and start Hue
    hue_config = load_config()
    hue = HueStreamer(
        bridge_ip=hue_config['bridge_ip'],
        username=hue_config['username'],
        clientkey=hue_config['clientkey'],
        entertainment_area_id=hue_config['entertainment_area_id'],
    )
    hue.start()

    # Initialize Ableton Link
    loop = asyncio.get_running_loop()
    link = Link(120, loop)  # Default 120 BPM
    link.enabled = True

    print("[LINK] Waiting for Ableton Link peers...")
    print("[LINK] Press Ctrl+C to exit")
    print()

    beat_count = 0

    # Handle shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        shutdown_event.set()

    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    try:
        while not shutdown_event.is_set():
            # Wait for next beat
            beat = await link.sync(1)
            beat_count += 1

            # Get current tempo from link
            # Note: aalink doesn't expose tempo directly, but we track beats

            # Pick color (change every 4 beats)
            color_idx = (beat_count // 4) % len(COLORS)
            color = COLORS[color_idx]

            # Flash on beat
            hue.set_all_lights(color[0], color[1], color[2])
            hue.flush()

            # Print beat info
            bar = (beat_count - 1) // 4 + 1
            beat_in_bar = ((beat_count - 1) % 4) + 1
            print(f"\r[BEAT] Bar {bar} Beat {beat_in_bar} | Color: {color}", end="", flush=True)

    except asyncio.CancelledError:
        pass
    finally:
        print("\n\n[SHUTDOWN] Stopping...")
        hue.stop()
        link.enabled = False


if __name__ == "__main__":
    asyncio.run(main())
