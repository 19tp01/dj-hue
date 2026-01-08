"""
Preset pattern collections.

Contains pre-built patterns for common DJ lighting effects.
"""

from .strudel_presets import get_strudel_presets
from .spatial_presets import get_spatial_presets


def get_all_presets() -> dict:
    """
    Get all preset patterns (Strudel + Spatial).

    Returns:
        Dict combining all preset patterns.
    """
    presets = {}
    presets.update(get_strudel_presets())
    presets.update(get_spatial_presets())
    return presets


__all__ = [
    "get_strudel_presets",
    "get_spatial_presets",
    "get_all_presets",
]
