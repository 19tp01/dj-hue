"""
Pattern metadata for capability declaration and filtering.

Patterns declare their zone requirements and fallback behaviors,
enabling the system to filter available patterns and gracefully
degrade when zones are missing.
"""

from dataclasses import dataclass, field
from enum import Enum


class FallbackStrategy(Enum):
    """How to handle patterns when required zones are missing."""

    USE_PRIMARY = "use_primary"
    """Run the primary zone's pattern on all available lights."""

    MERGE_LAYERS = "merge_layers"
    """Combine all zone layers into a single pattern."""

    DISABLE = "disable"
    """Hide/disable the pattern entirely."""

    REINTERPRET = "reinterpret"
    """Use an alternate single-zone version of the pattern."""


class EnergyLevel(Enum):
    """Energy level classification for pattern selection."""

    AMBIENT = 1
    """Background, atmospheric lighting."""

    LOW = 2
    """Calm, subtle movement."""

    MEDIUM = 3
    """Standard energy, visible activity."""

    HIGH = 4
    """High energy, attention-grabbing."""

    PEAK = 5
    """Maximum energy for drops/climaxes."""


@dataclass
class PatternCapability:
    """
    Declares what a pattern can do with different zone configurations.

    This metadata enables:
    - Filtering patterns based on available hardware
    - Showing "enhanced with ceiling" indicators
    - Automatic fallback when zones are missing

    Attributes:
        requires_zones: Zones that MUST be present (pattern disabled without them)
        enhanced_by_zones: Zones that improve the pattern but aren't required
        fallback_strategy: How to handle missing zones
        allow_reinterpret: Whether the pattern can be adapted for single-zone
        tags: Descriptive tags for filtering/organization
        energy: Energy level classification
    """

    requires_zones: list[str] = field(default_factory=list)
    enhanced_by_zones: list[str] = field(default_factory=list)
    fallback_strategy: FallbackStrategy = FallbackStrategy.USE_PRIMARY
    allow_reinterpret: bool = True
    tags: list[str] = field(default_factory=list)
    energy: EnergyLevel = EnergyLevel.MEDIUM

    def is_available(self, available_zones: list[str]) -> bool:
        """
        Check if pattern can run with the given zones.

        Returns True if all required zones are available.
        """
        return all(zone in available_zones for zone in self.requires_zones)

    def is_enhanced(self, available_zones: list[str]) -> bool:
        """
        Check if pattern would benefit from additional zones.

        Returns True if any enhancement zones are missing.
        """
        return any(zone not in available_zones for zone in self.enhanced_by_zones)

    def missing_required(self, available_zones: list[str]) -> list[str]:
        """Get list of required zones that are missing."""
        return [z for z in self.requires_zones if z not in available_zones]

    def missing_enhanced(self, available_zones: list[str]) -> list[str]:
        """Get list of enhancement zones that are missing."""
        return [z for z in self.enhanced_by_zones if z not in available_zones]

    def get_status(self, available_zones: list[str]) -> dict:
        """
        Get complete status for UI display.

        Returns:
            {
                "available": bool,
                "enhanced": bool,
                "degraded": bool,
                "missing_required": [...],
                "missing_enhanced": [...],
                "energy": "medium",
                "tags": [...]
            }
        """
        missing_req = self.missing_required(available_zones)
        missing_enh = self.missing_enhanced(available_zones)

        return {
            "available": len(missing_req) == 0,
            "enhanced": len(missing_enh) == 0,
            "degraded": len(missing_enh) > 0 and len(missing_req) == 0,
            "missing_required": missing_req,
            "missing_enhanced": missing_enh,
            "energy": self.energy.name.lower(),
            "tags": self.tags,
        }

    @classmethod
    def simple(cls, tags: list[str] | None = None, energy: EnergyLevel = EnergyLevel.MEDIUM) -> "PatternCapability":
        """Create a simple capability with no zone requirements."""
        return cls(
            requires_zones=[],
            enhanced_by_zones=[],
            fallback_strategy=FallbackStrategy.USE_PRIMARY,
            tags=tags or [],
            energy=energy,
        )

    @classmethod
    def ceiling_enhanced(
        cls,
        tags: list[str] | None = None,
        energy: EnergyLevel = EnergyLevel.MEDIUM,
    ) -> "PatternCapability":
        """Create a capability that's enhanced by ceiling but doesn't require it."""
        return cls(
            requires_zones=[],
            enhanced_by_zones=["ceiling"],
            fallback_strategy=FallbackStrategy.USE_PRIMARY,
            tags=tags or [],
            energy=energy,
        )

    @classmethod
    def requires_dual_zones(
        cls,
        tags: list[str] | None = None,
        energy: EnergyLevel = EnergyLevel.MEDIUM,
        allow_reinterpret: bool = True,
    ) -> "PatternCapability":
        """Create a capability that requires both ceiling and perimeter."""
        return cls(
            requires_zones=["ceiling", "perimeter"],
            enhanced_by_zones=[],
            fallback_strategy=FallbackStrategy.REINTERPRET if allow_reinterpret else FallbackStrategy.DISABLE,
            allow_reinterpret=allow_reinterpret,
            tags=tags or [],
            energy=energy,
        )
