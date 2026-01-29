"""
Common infrastructure for pattern systems.

Provides shared abstractions for light grouping and zones.
"""

from .groups import LightGroup, LightSetup, ZoneType
from .zones import ZoneConfig, ZoneDefinition, ZonePosition

__all__ = [
    # Groups
    "LightGroup",
    "LightSetup",
    "ZoneType",
    # Zones
    "ZoneConfig",
    "ZoneDefinition",
    "ZonePosition",
]
