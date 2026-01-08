"""
Core data structures for the Strudel-inspired pattern system.

This module contains the fundamental types used throughout the pattern system:
- TimeSpan: Represents a span of time in cycles
- LightValue: The properties of a light event (which light, color, intensity, envelope)
- LightHap: A "happening" - a light event with timing information
- LightContext: Runtime context providing light count and group definitions
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .envelope import Envelope
    from .automation import Automation
    from ..pattern_def import HSV


@dataclass(frozen=True)
class TimeSpan:
    """
    A span of time in cycles.

    Uses Fraction for precise rhythm math without floating-point drift.
    1 cycle = 1 bar (4 beats at 4/4 time).

    Examples:
        TimeSpan(0, 1)       # Full first cycle
        TimeSpan(0, 1/4)     # First quarter of cycle (beat 1)
        TimeSpan(1/2, 3/4)   # Third quarter of second beat
    """
    start: Fraction
    end: Fraction

    def __post_init__(self):
        # Convert to Fraction if needed (for convenience)
        object.__setattr__(self, 'start', Fraction(self.start))
        object.__setattr__(self, 'end', Fraction(self.end))

    @property
    def duration(self) -> Fraction:
        """Duration of this span."""
        return self.end - self.start

    def intersection(self, other: "TimeSpan") -> "TimeSpan | None":
        """
        Return the overlapping portion of two spans, or None if no overlap.
        """
        new_start = max(self.start, other.start)
        new_end = min(self.end, other.end)
        if new_start < new_end:
            return TimeSpan(new_start, new_end)
        return None

    def contains(self, time: Fraction) -> bool:
        """Check if a time point is within this span (inclusive start, exclusive end)."""
        return self.start <= time < self.end

    def shift(self, offset: Fraction) -> "TimeSpan":
        """Return a new span shifted by offset."""
        return TimeSpan(self.start + offset, self.end + offset)

    def scale(self, factor: Fraction) -> "TimeSpan":
        """Return a new span scaled by factor (times are multiplied)."""
        return TimeSpan(self.start * factor, self.end * factor)

    def __repr__(self) -> str:
        return f"TimeSpan({float(self.start):.3f}, {float(self.end):.3f})"


@dataclass
class LightValue:
    """
    The properties of a light event.

    Attributes:
        light_id: Which light this event affects (can be None for group references)
        group: Group name if this is a group reference (e.g., "all", "left")
        color: Target color (HSV)
        intensity: Base intensity multiplier (0.0-1.0)
        envelope: Optional envelope for time-varying intensity/color
        automation: Optional automation curve for continuous brightness control
    """
    light_id: int | None = None
    group: str | None = None
    color: "HSV | None" = None
    intensity: float = 1.0
    envelope: "Envelope | None" = None
    automation: "Automation | None" = None

    def with_color(self, color: "HSV") -> "LightValue":
        """Return a copy with updated color."""
        return LightValue(
            light_id=self.light_id,
            group=self.group,
            color=color,
            intensity=self.intensity,
            envelope=self.envelope,
            automation=self.automation,
        )

    def with_intensity(self, intensity: float) -> "LightValue":
        """Return a copy with updated intensity."""
        return LightValue(
            light_id=self.light_id,
            group=self.group,
            color=self.color,
            intensity=intensity,
            envelope=self.envelope,
            automation=self.automation,
        )

    def with_envelope(self, envelope: "Envelope") -> "LightValue":
        """Return a copy with updated envelope."""
        return LightValue(
            light_id=self.light_id,
            group=self.group,
            color=self.color,
            intensity=self.intensity,
            envelope=envelope,
            automation=self.automation,
        )

    def with_automation(self, automation: "Automation") -> "LightValue":
        """Return a copy with updated automation."""
        return LightValue(
            light_id=self.light_id,
            group=self.group,
            color=self.color,
            intensity=self.intensity,
            envelope=self.envelope,
            automation=automation,
        )


@dataclass
class LightHap:
    """
    A light "happening" - an event with timing information.

    Attributes:
        whole: The complete logical duration of this event (e.g., beat 0 to beat 1).
               Can be None for continuous events.
        part: The portion actually happening in this query window.
        value: The light properties for this event.

    The distinction between whole and part is important for envelopes:
    - whole defines the full event duration for envelope calculation
    - part defines what's visible in the current query window
    """
    whole: TimeSpan | None
    part: TimeSpan
    value: LightValue

    def whole_or_part(self) -> TimeSpan:
        """Return whole if available, otherwise part."""
        return self.whole if self.whole else self.part

    def with_value(self, value: LightValue) -> "LightHap":
        """Return a copy with updated value."""
        return LightHap(whole=self.whole, part=self.part, value=value)

    def with_part(self, part: TimeSpan) -> "LightHap":
        """Return a copy with updated part (keeps whole)."""
        return LightHap(whole=self.whole, part=part, value=self.value)

    def shift(self, offset: Fraction) -> "LightHap":
        """Return a copy with times shifted by offset."""
        return LightHap(
            whole=self.whole.shift(offset) if self.whole else None,
            part=self.part.shift(offset),
            value=self.value,
        )

    def scale(self, factor: Fraction) -> "LightHap":
        """Return a copy with times scaled by factor."""
        return LightHap(
            whole=self.whole.scale(Fraction(1) / factor) if self.whole else None,
            part=self.part.scale(Fraction(1) / factor),
            value=self.value,
        )

    def __repr__(self) -> str:
        light = self.value.light_id if self.value.light_id is not None else self.value.group
        return f"LightHap({self.part}, light={light})"


@dataclass
class LightContext:
    """
    Runtime context for pattern evaluation.

    Provides information about the light setup that patterns need
    to resolve group references and dynamic light counts.

    Attributes:
        num_lights: Total number of lights in the setup
        groups: Mapping of group names to light indices
        cycle_beats: Number of beats per cycle (default 4 for 4/4 time)
        zones: Mapping of zone names to light indices
        available_zones: List of configured zone names
    """
    num_lights: int
    groups: dict[str, list[int]] = field(default_factory=dict)
    cycle_beats: float = 4.0
    zones: dict[str, list[int]] = field(default_factory=dict)
    available_zones: list[str] = field(default_factory=list)

    def __post_init__(self):
        # Ensure "all" group exists
        if "all" not in self.groups:
            self.groups["all"] = list(range(self.num_lights))

    def resolve_group(self, name: str) -> list[int]:
        """
        Resolve a group name to light indices.

        Returns empty list if group not found.
        """
        return self.groups.get(name, [])

    def resolve_zone(self, name: str) -> list[int]:
        """
        Resolve a zone name to light indices.

        Returns empty list if zone not found.
        """
        return self.zones.get(name, [])

    def has_zone(self, name: str) -> bool:
        """Check if a zone is available."""
        return name in self.available_zones

    def has_dual_zones(self) -> bool:
        """Check if both ceiling and perimeter zones are available."""
        return "ceiling" in self.available_zones and "perimeter" in self.available_zones

    @classmethod
    def default(cls, num_lights: int = 6) -> "LightContext":
        """
        Create a default context with standard groups.

        For 6 lights, creates:
        - all: [0, 1, 2, 3, 4, 5]
        - left: [0, 1, 2]
        - right: [3, 4, 5]
        - odd: [1, 3, 5]
        - even: [0, 2, 4]
        """
        half = num_lights // 2
        return cls(
            num_lights=num_lights,
            groups={
                "all": list(range(num_lights)),
                "left": list(range(half)),
                "right": list(range(half, num_lights)),
                "odd": list(range(1, num_lights, 2)),
                "even": list(range(0, num_lights, 2)),
            },
        )

    @classmethod
    def with_zones(
        cls,
        num_lights: int,
        groups: dict[str, list[int]],
        zones: dict[str, list[int]],
    ) -> "LightContext":
        """
        Create a context with zone information.

        Args:
            num_lights: Total light count
            groups: Group name to light indices mapping
            zones: Zone name to light indices mapping
        """
        return cls(
            num_lights=num_lights,
            groups=groups,
            zones=zones,
            available_zones=list(zones.keys()),
        )
