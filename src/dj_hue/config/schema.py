"""Configuration dataclasses."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AudioInputConfig:
    """Audio input configuration."""
    device: Optional[str] = None  # Device name or None for default
    sample_rate: int = 44100
    block_size: int = 512
    channels: int = 1


@dataclass
class FrequencyBandConfig:
    """Frequency band definition."""
    name: str
    low_hz: float
    high_hz: float


@dataclass
class LightMappingConfig:
    """Mapping of a light to a frequency band."""
    light_id: int
    frequency_band: str
    base_hue: float = 0.0  # 0.0-1.0
    saturation: float = 1.0
    sensitivity: float = 1.0
    min_brightness: float = 0.1
    beat_reactive: bool = True


@dataclass
class LightGroupConfig:
    """Group of light mappings."""
    name: str
    lights: list[LightMappingConfig] = field(default_factory=list)


@dataclass
class HueConfig:
    """Philips Hue bridge configuration."""
    bridge_ip: str
    username: str
    clientkey: str
    entertainment_area_id: str
    fps: int = 25


@dataclass
class DJHueConfig:
    """Main application configuration."""
    audio: AudioInputConfig = field(default_factory=AudioInputConfig)
    hue: Optional[HueConfig] = None
    frequency_bands: list[FrequencyBandConfig] = field(default_factory=list)
    light_groups: list[LightGroupConfig] = field(default_factory=list)
    beat_detection: bool = True
    smoothing: float = 0.3

    def get_all_light_mappings(self) -> list[LightMappingConfig]:
        """Get flattened list of all light mappings."""
        mappings = []
        for group in self.light_groups:
            mappings.extend(group.lights)
        return mappings

    @classmethod
    def with_defaults(cls) -> "DJHueConfig":
        """Create config with sensible defaults."""
        return cls(
            frequency_bands=[
                FrequencyBandConfig("bass", 20, 250),
                FrequencyBandConfig("mid", 250, 2000),
                FrequencyBandConfig("high", 2000, 20000),
            ]
        )
