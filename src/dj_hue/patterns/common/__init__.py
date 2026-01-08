"""
Common infrastructure for pattern systems.

Provides shared abstractions for light grouping, zones, metadata, and registry.
"""

from .groups import LightGroup, LightSetup, ZoneType
from .zones import ZoneConfig, ZoneDefinition, ZonePosition
from .metadata import PatternCapability, FallbackStrategy, EnergyLevel
from .registry import PatternRegistry, PatternInfo

__all__ = [
    # Groups
    "LightGroup",
    "LightSetup",
    "ZoneType",
    # Zones
    "ZoneConfig",
    "ZoneDefinition",
    "ZonePosition",
    # Metadata
    "PatternCapability",
    "FallbackStrategy",
    "EnergyLevel",
    # Registry
    "PatternRegistry",
    "PatternInfo",
]
