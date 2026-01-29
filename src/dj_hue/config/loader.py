"""Configuration file loading and saving."""

from pathlib import Path
from typing import Any
import yaml

from .schema import (
    DJHueConfig,
    AudioInputConfig,
    HueConfig,
    FrequencyBandConfig,
    LightMappingConfig,
    LightGroupConfig,
)


def load_config(config_path: Path) -> DJHueConfig:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    # Parse audio config
    audio_data = data.get("audio", {})
    audio = AudioInputConfig(
        device=audio_data.get("device"),
        sample_rate=audio_data.get("sample_rate", 44100),
        block_size=audio_data.get("block_size", 512),
        channels=audio_data.get("channels", 1),
    )

    # Parse Hue config
    hue = None
    if "hue" in data and data["hue"]:
        hue_data = data["hue"]
        hue = HueConfig(
            bridge_ip=hue_data["bridge_ip"],
            username=hue_data["username"],
            clientkey=hue_data["clientkey"],
            entertainment_area_id=hue_data["entertainment_area_id"],
            fps=hue_data.get("fps", 25),
        )

    # Parse frequency bands
    bands = []
    for band_data in data.get("frequency_bands", []):
        bands.append(FrequencyBandConfig(
            name=band_data["name"],
            low_hz=band_data["low_hz"],
            high_hz=band_data["high_hz"],
        ))

    # Use defaults if no bands specified
    if not bands:
        bands = [
            FrequencyBandConfig("bass", 20, 250),
            FrequencyBandConfig("mid", 250, 2000),
            FrequencyBandConfig("high", 2000, 20000),
        ]

    # Parse light groups
    groups = []
    for group_data in data.get("light_groups", []):
        lights = []
        for light_data in group_data.get("lights", []):
            lights.append(LightMappingConfig(
                light_id=light_data["light_id"],
                frequency_band=light_data["frequency_band"],
                base_hue=light_data.get("base_hue", 0.0),
                saturation=light_data.get("saturation", 1.0),
                sensitivity=light_data.get("sensitivity", 1.0),
                min_brightness=light_data.get("min_brightness", 0.1),
                beat_reactive=light_data.get("beat_reactive", True),
            ))
        groups.append(LightGroupConfig(name=group_data["name"], lights=lights))

    return DJHueConfig(
        audio=audio,
        hue=hue,
        frequency_bands=bands,
        light_groups=groups,
        beat_detection=data.get("beat_detection", True),
        smoothing=data.get("smoothing", 0.3),
    )


def save_config(config: DJHueConfig, config_path: Path) -> None:
    """Save configuration to YAML file."""
    data: dict[str, Any] = {
        "audio": {
            "device": config.audio.device,
            "sample_rate": config.audio.sample_rate,
            "block_size": config.audio.block_size,
            "channels": config.audio.channels,
        },
        "frequency_bands": [
            {"name": b.name, "low_hz": b.low_hz, "high_hz": b.high_hz}
            for b in config.frequency_bands
        ],
        "light_groups": [
            {
                "name": g.name,
                "lights": [
                    {
                        "light_id": l.light_id,
                        "frequency_band": l.frequency_band,
                        "base_hue": l.base_hue,
                        "saturation": l.saturation,
                        "sensitivity": l.sensitivity,
                        "min_brightness": l.min_brightness,
                        "beat_reactive": l.beat_reactive,
                    }
                    for l in g.lights
                ],
            }
            for g in config.light_groups
        ],
        "beat_detection": config.beat_detection,
        "smoothing": config.smoothing,
    }

    if config.hue:
        data["hue"] = {
            "bridge_ip": config.hue.bridge_ip,
            "username": config.hue.username,
            "clientkey": config.hue.clientkey,
            "entertainment_area_id": config.hue.entertainment_area_id,
            "fps": config.hue.fps,
        }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
