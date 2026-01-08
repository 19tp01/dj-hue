"""
Spatial pattern components for zone-aware lighting effects.

Provides LayeredPattern for defining zone-specific behaviors
with automatic fallback when zones are missing.
"""

from .layered import LayeredPattern, ZoneLayer
from .combiner import (
    combine_zone_layers,
    remap_pattern_to_zone,
    create_spatial_delay_pattern,
    create_echo_pattern,
    create_alternating_zones_pattern,
)

__all__ = [
    "LayeredPattern",
    "ZoneLayer",
    "combine_zone_layers",
    "remap_pattern_to_zone",
    "create_spatial_delay_pattern",
    "create_echo_pattern",
    "create_alternating_zones_pattern",
]
