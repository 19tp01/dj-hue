"""
Pattern registry with zone-aware filtering.

Central registry for all patterns (classic, Strudel, and layered spatial).
Handles filtering based on available zones and provides status information
for UI display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .strudel.layered import LayeredPattern
    from .strudel.pattern import LightPattern
    from .zones import ZoneConfig


@dataclass
class PatternInfo:
    """Information about a registered pattern for UI display."""
    name: str
    description: str
    available: bool
    enhanced: bool
    degraded: bool
    missing_zones: list[str]
    tags: list[str]
    energy: str
    pattern_type: str  # "classic", "strudel", or "layered"


class PatternRegistry:
    """
    Central registry for all patterns with zone-aware filtering.

    Manages registration and lookup of:
    - Classic patterns (Pattern instances)
    - Strudel patterns (LightPattern wrapped)
    - Layered spatial patterns (LayeredPattern instances)

    Provides filtering based on available zones and status information
    for UI display.
    """

    def __init__(self, zone_config: "ZoneConfig | None" = None):
        """
        Initialize the registry.

        Args:
            zone_config: Zone configuration for filtering. If None,
                        all patterns are considered available.
        """
        self._zone_config = zone_config
        self._layered_patterns: dict[str, "LayeredPattern"] = {}
        self._pattern_order: list[str] = []

    @property
    def available_zones(self) -> list[str]:
        """Get list of available zone names."""
        if self._zone_config:
            return self._zone_config.available_zones()
        return []

    def set_zone_config(self, zone_config: "ZoneConfig | None") -> None:
        """Update the zone configuration."""
        self._zone_config = zone_config

    def register(self, pattern: "LayeredPattern") -> None:
        """
        Register a layered pattern.

        Args:
            pattern: LayeredPattern instance to register
        """
        self._layered_patterns[pattern.name] = pattern
        if pattern.name not in self._pattern_order:
            self._pattern_order.append(pattern.name)

    def register_all(self, patterns: dict[str, "LayeredPattern"]) -> None:
        """Register multiple patterns at once."""
        for name, pattern in patterns.items():
            self.register(pattern)

    def unregister(self, name: str) -> bool:
        """
        Remove a pattern from the registry.

        Returns True if pattern was found and removed.
        """
        if name in self._layered_patterns:
            del self._layered_patterns[name]
            if name in self._pattern_order:
                self._pattern_order.remove(name)
            return True
        return False

    def get_layered_pattern(self, name: str) -> "LayeredPattern | None":
        """Get a layered pattern by name."""
        return self._layered_patterns.get(name)

    def get_effective_pattern(self, name: str) -> "LightPattern | None":
        """
        Get the effective LightPattern for a name.

        Returns the pattern with zone-based fallback applied.
        """
        pattern = self._layered_patterns.get(name)
        if pattern:
            return pattern.get_effective_pattern(self.available_zones)
        return None

    def get_all_layered(self) -> list["LayeredPattern"]:
        """Get all registered layered patterns in order."""
        return [self._layered_patterns[name] for name in self._pattern_order
                if name in self._layered_patterns]

    def get_available_patterns(self) -> list["LayeredPattern"]:
        """
        Get patterns that work with current zone configuration.

        Excludes patterns whose requirements aren't met.
        """
        return [
            p for p in self.get_all_layered()
            if p.is_available(self.available_zones)
        ]

    def get_unavailable_patterns(self) -> list["LayeredPattern"]:
        """
        Get patterns that don't work with current zone configuration.

        These are patterns with unmet requirements.
        """
        return [
            p for p in self.get_all_layered()
            if not p.is_available(self.available_zones)
        ]

    def get_enhanced_patterns(self) -> list[tuple["LayeredPattern", list[str]]]:
        """
        Get available patterns that would benefit from additional zones.

        Returns:
            List of (pattern, missing_zones) tuples
        """
        result = []
        for p in self.get_all_layered():
            if p.is_available(self.available_zones) and p.is_enhanced(self.available_zones):
                missing = p.capability.missing_enhanced(self.available_zones)
                result.append((p, missing))
        return result

    def get_pattern_info(self, name: str) -> PatternInfo | None:
        """
        Get detailed information about a pattern.

        Returns None if pattern not found.
        """
        pattern = self._layered_patterns.get(name)
        if not pattern:
            return None

        status = pattern.get_status(self.available_zones)

        return PatternInfo(
            name=pattern.name,
            description=pattern.description,
            available=status["available"],
            enhanced=status["enhanced"],
            degraded=status["degraded"],
            missing_zones=status.get("missing_enhanced", []) + status.get("missing_required", []),
            tags=status.get("tags", []),
            energy=status.get("energy", "medium"),
            pattern_type="layered",
        )

    def get_all_pattern_info(self) -> list[PatternInfo]:
        """Get information about all registered patterns."""
        return [
            info for name in self._pattern_order
            if (info := self.get_pattern_info(name)) is not None
        ]

    def get_available_pattern_names(self) -> list[str]:
        """Get names of all available patterns."""
        return [p.name for p in self.get_available_patterns()]

    def filter_by_tags(self, tags: list[str], match_all: bool = False) -> list["LayeredPattern"]:
        """
        Filter patterns by tags.

        Args:
            tags: Tags to filter by
            match_all: If True, pattern must have all tags. If False, any tag matches.

        Returns:
            List of matching patterns
        """
        result = []
        for pattern in self.get_available_patterns():
            pattern_tags = set(pattern.capability.tags)
            if match_all:
                if all(tag in pattern_tags for tag in tags):
                    result.append(pattern)
            else:
                if any(tag in pattern_tags for tag in tags):
                    result.append(pattern)
        return result

    def filter_by_energy(
        self,
        min_energy: int = 1,
        max_energy: int = 5,
    ) -> list["LayeredPattern"]:
        """
        Filter patterns by energy level.

        Args:
            min_energy: Minimum energy level (1-5)
            max_energy: Maximum energy level (1-5)

        Returns:
            List of patterns within energy range
        """
        return [
            p for p in self.get_available_patterns()
            if min_energy <= p.capability.energy.value <= max_energy
        ]

    def __len__(self) -> int:
        """Number of registered patterns."""
        return len(self._layered_patterns)

    def __contains__(self, name: str) -> bool:
        """Check if a pattern is registered."""
        return name in self._layered_patterns
