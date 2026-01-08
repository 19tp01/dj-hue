"""
Layered pattern system for zone-aware spatial effects.

LayeredPattern allows patterns to define different behaviors per zone
(ceiling, perimeter) with automatic fallback when zones are missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .pattern import LightPattern
from .constructors import light, stack

if TYPE_CHECKING:
    from .core import LightContext
    from ..metadata import PatternCapability, FallbackStrategy


@dataclass
class ZoneLayer:
    """
    A pattern layer targeting a specific zone.

    Attributes:
        zone: Target zone name ("ceiling" or "perimeter")
        pattern: The LightPattern to run on this zone
        timing_offset: Delay in beats (for spatial effects like lightning)
        intensity_scale: Relative intensity multiplier (0.0-1.0)
    """
    zone: str
    pattern: LightPattern
    timing_offset: float = 0.0
    intensity_scale: float = 1.0

    def get_pattern(self) -> LightPattern:
        """Get the pattern with timing offset applied."""
        pattern = self.pattern

        # Apply timing offset
        if self.timing_offset > 0:
            pattern = pattern.late(self.timing_offset)
        elif self.timing_offset < 0:
            pattern = pattern.early(-self.timing_offset)

        # Apply intensity scaling
        if self.intensity_scale != 1.0:
            pattern = pattern.intensity(self.intensity_scale)

        return pattern


@dataclass
class LayeredPattern:
    """
    A pattern with zone-specific behaviors and fallback.

    This is the primary way to define spatial patterns that can
    gracefully degrade when zones are missing.

    Attributes:
        name: Pattern identifier
        description: Human-readable description
        capability: Zone requirements and fallback behavior
        layers: Zone-specific pattern layers
        fallback_pattern: Single-zone version when zones are missing
        reinterpreted_pattern: Alternative single-zone version
    """
    name: str
    description: str
    capability: "PatternCapability"
    layers: dict[str, ZoneLayer] = field(default_factory=dict)
    fallback_pattern: LightPattern | None = None
    reinterpreted_pattern: LightPattern | None = None

    def is_available(self, available_zones: list[str]) -> bool:
        """Check if pattern can run with the given zones."""
        return self.capability.is_available(available_zones)

    def is_enhanced(self, available_zones: list[str]) -> bool:
        """Check if pattern would benefit from more zones."""
        return self.capability.is_enhanced(available_zones)

    def get_status(self, available_zones: list[str]) -> dict:
        """Get complete status for UI display."""
        status = self.capability.get_status(available_zones)
        status["name"] = self.name
        status["description"] = self.description
        return status

    def get_effective_pattern(self, available_zones: list[str]) -> LightPattern | None:
        """
        Get the appropriate pattern based on available zones.

        Decision logic:
        1. If all required zones available → combine layers
        2. If enhanced zones missing → use available layers + fallback
        3. If required zones missing + allow_reinterpret → use reinterpreted
        4. If required zones missing + !allow_reinterpret → None (disable)

        Args:
            available_zones: List of zone names that are configured

        Returns:
            LightPattern to render, or None if unavailable
        """
        from ..metadata import FallbackStrategy

        # Check if required zones are present
        missing_required = self.capability.missing_required(available_zones)

        if missing_required:
            # Required zones are missing
            if self.capability.fallback_strategy == FallbackStrategy.DISABLE:
                return None

            if self.capability.fallback_strategy == FallbackStrategy.REINTERPRET:
                if self.capability.allow_reinterpret and self.reinterpreted_pattern:
                    return self.reinterpreted_pattern
                return None

            # USE_PRIMARY or MERGE_LAYERS with missing requirements
            # Fall back to primary pattern if available
            if self.fallback_pattern:
                return self.fallback_pattern
            return None

        # All required zones are present
        # Check which layers we can use
        active_layers: list[LightPattern] = []
        missing_enhanced = self.capability.missing_enhanced(available_zones)

        for zone_name, layer in self.layers.items():
            if zone_name in available_zones:
                # Zone is available - use its layer
                active_layers.append(layer.get_pattern())

        # If we're missing enhancement zones, add fallback for those
        if missing_enhanced and self.fallback_pattern:
            # The fallback pattern supplements the missing zones
            if self.capability.fallback_strategy == FallbackStrategy.MERGE_LAYERS:
                active_layers.append(self.fallback_pattern)

        # Combine all active layers
        if not active_layers:
            return self.fallback_pattern or light("")

        if len(active_layers) == 1:
            return active_layers[0]

        return stack(*active_layers)

    def add_layer(
        self,
        zone: str,
        pattern: LightPattern,
        timing_offset: float = 0.0,
        intensity_scale: float = 1.0,
    ) -> "LayeredPattern":
        """
        Add a zone layer (returns self for chaining).

        Args:
            zone: Target zone name
            pattern: Pattern for this zone
            timing_offset: Beat delay for spatial effects
            intensity_scale: Intensity multiplier
        """
        self.layers[zone] = ZoneLayer(
            zone=zone,
            pattern=pattern,
            timing_offset=timing_offset,
            intensity_scale=intensity_scale,
        )
        return self

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        capability: "PatternCapability",
        ceiling: LightPattern | None = None,
        perimeter: LightPattern | None = None,
        ceiling_delay: float = 0.0,
        perimeter_delay: float = 0.0,
        fallback: LightPattern | None = None,
        reinterpreted: LightPattern | None = None,
    ) -> "LayeredPattern":
        """
        Convenience factory for creating layered patterns.

        Args:
            name: Pattern name
            description: Human-readable description
            capability: Zone requirements
            ceiling: Pattern for ceiling zone
            perimeter: Pattern for perimeter zone
            ceiling_delay: Timing offset for ceiling (beats)
            perimeter_delay: Timing offset for perimeter (beats)
            fallback: Single-zone fallback pattern
            reinterpreted: Alternative single-zone version
        """
        pattern = cls(
            name=name,
            description=description,
            capability=capability,
            fallback_pattern=fallback,
            reinterpreted_pattern=reinterpreted,
        )

        if ceiling:
            pattern.add_layer("ceiling", ceiling, timing_offset=ceiling_delay)

        if perimeter:
            pattern.add_layer("perimeter", perimeter, timing_offset=perimeter_delay)

        return pattern
