"""Configuration schema and loading."""

from .schema import (
    DJHueConfig,
    AudioInputConfig,
    HueConfig,
    FrequencyBandConfig,
    LightMappingConfig,
    LightGroupConfig,
)
from .loader import load_config, save_config

__all__ = [
    "DJHueConfig",
    "AudioInputConfig",
    "HueConfig",
    "FrequencyBandConfig",
    "LightMappingConfig",
    "LightGroupConfig",
    "load_config",
    "save_config",
]
