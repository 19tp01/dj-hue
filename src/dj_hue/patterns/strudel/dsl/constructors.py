"""
Pattern constructors for the Strudel pattern system.

Provides the main entry points for creating patterns:
- light() - create pattern from mini notation
- stack() - layer patterns (parallel)
- cat() - sequence patterns (one per cycle)
"""

from __future__ import annotations

from fractions import Fraction
from typing import Sequence

from ..core.types import TimeSpan, LightHap, LightValue, LightContext
from ..core.pattern import LightPattern
from .parser import parse_to_query_data


def light(notation: str | list[int]) -> LightPattern:
    """
    Create a pattern from mini notation or a list of light indices.

    Args:
        notation: Either a mini notation string or list of light indices

    Examples:
        light("0 1 2 3 4 5")      # Sequence through lights
        light("all")              # All lights, full cycle
        light("all ~*15")         # All lights on beat 1, rest for 15
        light("left right")       # Left then right
        light([0, 1, 2])          # Same as "0 1 2"

    Returns:
        LightPattern that can be further transformed
    """
    if isinstance(notation, list):
        # Convert list to notation string
        notation = " ".join(str(i) for i in notation)

    # Parse the notation
    event_data = parse_to_query_data(notation)

    def query_light(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
        result = []

        # Get the cycle range we need to cover
        cycle_start = int(span.start)
        cycle_end = int(span.end) + 1

        for cycle in range(cycle_start, cycle_end):
            cycle_offset = Fraction(cycle)

            for start, end, light_id, group in event_data:
                # Shift event times to this cycle
                event_start = start + cycle_offset
                event_end = end + cycle_offset
                whole = TimeSpan(event_start, event_end)

                # Check if this event intersects with query span
                intersection = whole.intersection(span)
                if intersection:
                    value = LightValue(light_id=light_id, group=group)
                    result.append(LightHap(
                        whole=whole,
                        part=intersection,
                        value=value,
                    ))

        return result

    return LightPattern(query_light)


def stack(*patterns: LightPattern) -> LightPattern:
    """
    Combine multiple patterns to play simultaneously (layer them).

    Example:
        stack(
            light("left").color("red"),
            light("right").color("blue").late(0.5),
        )

    Returns:
        Combined LightPattern
    """
    if not patterns:
        return light("")  # Empty pattern

    if len(patterns) == 1:
        return patterns[0]

    def query_stack(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
        result = []
        for pattern in patterns:
            result.extend(pattern.query(span, ctx))
        return result

    return LightPattern(query_stack)


def cat(*patterns: LightPattern) -> LightPattern:
    """
    Concatenate patterns: each plays for one cycle in sequence.

    Example:
        cat(
            light("all").fast(2),   # Cycle 0
            light("all").fast(4),   # Cycle 1
            light("all").fast(8),   # Cycle 2
        )

    Use .slow(n) to make each pattern last n cycles:
        cat(p1, p2, p3, p4).slow(2)  # Each pattern gets 2 cycles

    Returns:
        Concatenated LightPattern
    """
    if not patterns:
        return light("")  # Empty pattern

    if len(patterns) == 1:
        return patterns[0]

    n = len(patterns)

    def query_cat(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
        result = []

        # Get the cycle range we need to cover
        cycle_start = int(span.start)
        cycle_end = int(span.end) + 1

        for cycle in range(cycle_start, cycle_end):
            # Which pattern plays in this cycle?
            pattern_idx = cycle % n
            pattern = patterns[pattern_idx]

            # Query span for this cycle
            cycle_span = TimeSpan(Fraction(cycle), Fraction(cycle + 1))
            intersection = cycle_span.intersection(span)

            if intersection:
                # Query the pattern for its portion, shifted to cycle 0
                local_start = intersection.start - Fraction(cycle)
                local_end = intersection.end - Fraction(cycle)
                local_span = TimeSpan(local_start, local_end)

                haps = pattern.query(local_span, ctx)

                # Shift results back to the actual cycle
                for h in haps:
                    result.append(h.shift(Fraction(cycle)))

        return result

    return LightPattern(query_cat)


# Convenience aliases
def all_lights() -> LightPattern:
    """Shorthand for light("all") - all lights for full cycle."""
    return light("all")


def sequence(*light_ids: int) -> LightPattern:
    """Shorthand for light([...]) - sequence through specified lights."""
    return light(list(light_ids))


def ceiling(notation: str = "all") -> LightPattern:
    """
    Create a pattern targeting the ceiling zone.

    This is shorthand for `light(notation).zone("ceiling")`.
    If the ceiling zone doesn't exist, returns no events (black).

    Args:
        notation: Mini notation for which lights (default "all")

    Examples:
        ceiling()                     # All ceiling lights
        ceiling().color("blue")       # Blue ceiling
        ceiling().seq().fast(2)       # Fast chase on ceiling
        ceiling("odd")                # Odd lights within ceiling zone

        # Combine with other zones
        stack(
            ceiling().color("white").fast(4),
            perimeter().color("blue").slow(2),
        )
    """
    return light(notation).zone("ceiling")


def perimeter(notation: str = "all") -> LightPattern:
    """
    Create a pattern targeting the perimeter zone.

    This is shorthand for `light(notation).zone("perimeter")`.
    If the perimeter zone doesn't exist, returns no events (black).

    Args:
        notation: Mini notation for which lights (default "all")

    Examples:
        perimeter()                   # All perimeter lights
        perimeter().color("red")      # Red perimeter
        perimeter().seq().shuffle()   # Random sequence around perimeter

        # Combine with other zones
        stack(
            ceiling().strobe(),
            perimeter().chase(),
        )
    """
    return light(notation).zone("perimeter")
