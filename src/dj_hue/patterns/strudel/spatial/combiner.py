"""
Zone layer combiner for runtime pattern composition.

Handles combining multiple zone-specific patterns into a single
renderable pattern, with proper handling of timing offsets and
fallback behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.pattern import LightPattern
from ..dsl.constructors import light, stack

if TYPE_CHECKING:
    from .layered import ZoneLayer
    from ..core.types import LightContext


def combine_zone_layers(
    layers: dict[str, "ZoneLayer"],
    available_zones: list[str],
    fallback: LightPattern | None = None,
) -> LightPattern:
    """
    Combine zone layers into a single pattern based on availability.

    For each zone:
    - If zone available: use its layer (with timing offset applied)
    - If zone missing: skip it

    If all zones are missing and a fallback is provided, use the fallback.

    Args:
        layers: Dict mapping zone names to ZoneLayer instances
        available_zones: List of zones that are currently configured
        fallback: Pattern to use if no layers can be applied

    Returns:
        Combined LightPattern ready for rendering
    """
    patterns_to_stack: list[LightPattern] = []

    for zone_name, layer in layers.items():
        if zone_name in available_zones:
            # Zone is available - use its pattern with transforms applied
            patterns_to_stack.append(layer.get_pattern())

    # If no layers could be used, fall back
    if not patterns_to_stack:
        if fallback:
            return fallback
        return light("")  # Empty pattern

    # Single layer - no need to stack
    if len(patterns_to_stack) == 1:
        return patterns_to_stack[0]

    # Multiple layers - combine them
    return stack(*patterns_to_stack)


def remap_pattern_to_zone(
    pattern: LightPattern,
    zone_indices: list[int],
) -> LightPattern:
    """
    Remap a pattern that targets "all" to only affect specific zone indices.

    This is useful when a fallback pattern needs to be constrained
    to only one zone's lights.

    Note: This is a best-effort transform. Patterns that use specific
    group names may not remap correctly.

    Args:
        pattern: Pattern to remap
        zone_indices: Light indices that should be affected

    Returns:
        Pattern constrained to the zone's lights
    """
    # For now, this is a no-op - the pattern will run on its defined targets
    # In the future, we could implement actual index remapping
    # by wrapping the pattern's query function
    return pattern


def create_spatial_delay_pattern(
    source_pattern: LightPattern,
    target_pattern: LightPattern,
    delay_beats: float,
) -> LightPattern:
    """
    Create a pattern where source triggers first, then target follows with delay.

    Useful for effects like lightning (ceiling flashes, then room illuminates).

    Args:
        source_pattern: Pattern that triggers first (e.g., ceiling flash)
        target_pattern: Pattern that follows (e.g., room illumination)
        delay_beats: Delay between source and target in beats

    Returns:
        Combined pattern with proper timing
    """
    delayed_target = target_pattern.late(delay_beats)
    return stack(source_pattern, delayed_target)


def create_echo_pattern(
    primary_pattern: LightPattern,
    echo_pattern: LightPattern,
    delay_beats: float,
    echo_intensity: float = 0.7,
) -> LightPattern:
    """
    Create a pattern where primary triggers, then echo follows with reduced intensity.

    Useful for effects like heartbeat (ceiling beats, perimeter echoes softer).

    Args:
        primary_pattern: Main pattern at full intensity
        echo_pattern: Pattern that echoes
        delay_beats: Delay for the echo
        echo_intensity: Intensity multiplier for echo (0.0-1.0)

    Returns:
        Combined pattern with echo effect
    """
    echo = echo_pattern.late(delay_beats).intensity(echo_intensity)
    return stack(primary_pattern, echo)


def create_alternating_zones_pattern(
    zone_a_pattern: LightPattern,
    zone_b_pattern: LightPattern,
    beats_per_alternate: float = 0.5,
) -> LightPattern:
    """
    Create a pattern that alternates between two zone patterns.

    Useful for effects like bullseye (ceiling on, perimeter off, then swap).

    Args:
        zone_a_pattern: First zone pattern
        zone_b_pattern: Second zone pattern
        beats_per_alternate: How often to alternate (in beats)

    Returns:
        Alternating pattern
    """
    from ..dsl.constructors import cat

    # Create alternating on/off patterns
    # This uses cat to sequence A-on + B-off, then A-off + B-on
    # and speeds it up to achieve the desired alternation rate

    cycle_a = stack(
        zone_a_pattern,
        light(""),  # B is off
    )
    cycle_b = stack(
        light(""),  # A is off
        zone_b_pattern,
    )

    # Combine and adjust timing
    combined = cat(cycle_a, cycle_b)

    # Scale to achieve desired alternation rate
    # beats_per_alternate of 0.5 means 2 alternations per beat = fast(2)
    if beats_per_alternate != 1.0:
        speed_factor = 1.0 / beats_per_alternate
        combined = combined.fast(speed_factor)

    return combined
