"""
Automation curves for time-varying brightness and other parameters.

Similar to automation lanes in a DAW (like Soundswitch), this lets you
define explicit value transitions over beat positions using curves.

Example usage:
    # Simple linear ramp from beat 0 to beat 1
    pattern.brightness(ramp(0, 1, 0.0, 1.0))

    # Build complex automation with keyframes
    pattern.brightness(
        automation()
            .ramp(0, 1, 0.0, 1.0)      # Beat 0->1: fade in
            .hold(1, 2)                 # Beat 1->2: hold at 1.0
            .ramp(2, 4, 1.0, 0.0, "ease_out")  # Beat 2->4: fade out
    )

    # Shorthand with keyframes
    pattern.brightness(keyframes([
        (0, 0.0),       # Beat 0: 0%
        (1, 1.0),       # Beat 1: 100% (linear from previous)
        (2, 1.0),       # Beat 2: 100% (hold)
        (4, 0.0),       # Beat 4: 0% (linear fade)
    ]))
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class CurveType(Enum):
    """Available curve types for automation segments."""
    LINEAR = "linear"
    EASE_IN = "ease_in"           # Slow start, fast end (quadratic)
    EASE_OUT = "ease_out"         # Fast start, slow end (quadratic)
    EASE_IN_OUT = "ease_in_out"   # Slow start and end (smoothstep)
    SMOOTH = "smooth"             # Alias for ease_in_out
    EXPONENTIAL = "exponential"   # Exponential curve
    LOGARITHMIC = "logarithmic"   # Logarithmic curve
    SINE = "sine"                 # Sine wave (quarter cycle)
    HOLD = "hold"                 # Hold start value, jump at end


def _apply_curve(t: float, curve: CurveType) -> float:
    """
    Apply curve function to normalized time t (0.0-1.0).

    Returns: Curved value (0.0-1.0)
    """
    t = max(0.0, min(1.0, t))

    if curve == CurveType.LINEAR:
        return t

    elif curve == CurveType.EASE_IN:
        # Quadratic ease in: slow start
        return t * t

    elif curve == CurveType.EASE_OUT:
        # Quadratic ease out: slow end
        return 1.0 - (1.0 - t) * (1.0 - t)

    elif curve in (CurveType.EASE_IN_OUT, CurveType.SMOOTH):
        # Smoothstep: slow start and end
        return t * t * (3.0 - 2.0 * t)

    elif curve == CurveType.EXPONENTIAL:
        # Exponential: starts very slow, accelerates dramatically
        if t <= 0:
            return 0.0
        return (math.exp(t * 3) - 1) / (math.e ** 3 - 1)

    elif curve == CurveType.LOGARITHMIC:
        # Logarithmic: fast start, slow end
        if t <= 0:
            return 0.0
        return math.log(t * (math.e - 1) + 1)

    elif curve == CurveType.SINE:
        # Sine quarter wave: smooth S-curve
        return math.sin(t * math.pi / 2)

    elif curve == CurveType.HOLD:
        # Hold start value until the very end
        return 0.0 if t < 1.0 else 1.0

    return t


@dataclass
class Segment:
    """
    A single automation segment between two beat positions.

    Attributes:
        start_beat: Starting beat position
        end_beat: Ending beat position
        start_value: Value at start (0.0-1.0)
        end_value: Value at end (0.0-1.0)
        curve: Curve type for interpolation
    """
    start_beat: float
    end_beat: float
    start_value: float
    end_value: float
    curve: CurveType = CurveType.LINEAR

    def get_value(self, beat: float) -> float | None:
        """
        Get the automation value at a given beat position.

        Returns None if beat is outside this segment.
        """
        if beat < self.start_beat or beat > self.end_beat:
            return None

        # Calculate normalized position within segment
        duration = self.end_beat - self.start_beat
        if duration <= 0:
            return self.end_value

        t = (beat - self.start_beat) / duration
        curved_t = _apply_curve(t, self.curve)

        # Interpolate between start and end values
        return self.start_value + (self.end_value - self.start_value) * curved_t


@dataclass
class Automation:
    """
    A collection of automation segments defining a brightness curve.

    Segments should be contiguous (end of one = start of next) but
    gaps are allowed (returns None for gaps).

    Example:
        auto = Automation([
            Segment(0, 1, 0.0, 1.0, CurveType.LINEAR),
            Segment(1, 2, 1.0, 1.0, CurveType.HOLD),
            Segment(2, 4, 1.0, 0.0, CurveType.EASE_OUT),
        ])
        value = auto.get_value(1.5)  # Returns 1.0
    """
    segments: list[Segment] = field(default_factory=list)
    loop_beats: float | None = None  # If set, automation loops every N beats

    def get_value(self, beat: float) -> float | None:
        """
        Get the automation value at a given beat position.

        Returns None if no segment covers this beat.
        """
        # Handle looping
        if self.loop_beats is not None and self.loop_beats > 0:
            beat = beat % self.loop_beats

        for segment in self.segments:
            value = segment.get_value(beat)
            if value is not None:
                return value

        return None

    def get_value_or_default(self, beat: float, default: float = 1.0) -> float:
        """Get value with a fallback default for gaps."""
        value = self.get_value(beat)
        return value if value is not None else default

    @property
    def duration(self) -> float:
        """Total duration in beats (from first segment start to last segment end)."""
        if not self.segments:
            return 0.0
        return max(s.end_beat for s in self.segments) - min(s.start_beat for s in self.segments)

    @property
    def start_beat(self) -> float:
        """First beat position."""
        if not self.segments:
            return 0.0
        return min(s.start_beat for s in self.segments)

    @property
    def end_beat(self) -> float:
        """Last beat position."""
        if not self.segments:
            return 0.0
        return max(s.end_beat for s in self.segments)


class AutomationBuilder:
    """
    Fluent builder for creating automation curves.

    Example:
        auto = automation().ramp(0, 1, 0.0, 1.0).hold(1, 2).ramp(2, 4, 1.0, 0.0).build()
    """

    def __init__(self):
        self._segments: list[Segment] = []
        self._loop_beats: float | None = None
        self._current_value: float = 0.0
        self._current_beat: float = 0.0

    def ramp(
        self,
        start_beat: float,
        end_beat: float,
        start_value: float,
        end_value: float,
        curve: str | CurveType = CurveType.LINEAR,
    ) -> AutomationBuilder:
        """
        Add a ramp segment from start_value to end_value.

        Args:
            start_beat: Starting beat position
            end_beat: Ending beat position
            start_value: Value at start (0.0-1.0)
            end_value: Value at end (0.0-1.0)
            curve: Curve type ("linear", "ease_in", "ease_out", "smooth", etc.)
        """
        if isinstance(curve, str):
            curve = CurveType(curve)

        self._segments.append(Segment(
            start_beat=start_beat,
            end_beat=end_beat,
            start_value=start_value,
            end_value=end_value,
            curve=curve,
        ))
        self._current_beat = end_beat
        self._current_value = end_value
        return self

    def hold(
        self,
        start_beat: float,
        end_beat: float,
        value: float | None = None,
    ) -> AutomationBuilder:
        """
        Add a hold segment at constant value.

        If value is None, uses the end value of the previous segment.
        """
        if value is None:
            value = self._current_value

        self._segments.append(Segment(
            start_beat=start_beat,
            end_beat=end_beat,
            start_value=value,
            end_value=value,
            curve=CurveType.HOLD,
        ))
        self._current_beat = end_beat
        self._current_value = value
        return self

    def to(
        self,
        beat: float,
        value: float,
        curve: str | CurveType = CurveType.LINEAR,
    ) -> AutomationBuilder:
        """
        Shorthand: add segment from current position to new beat/value.

        Example:
            automation().at(0, 0).to(1, 1.0).to(2, 0.5).to(4, 0)
        """
        if isinstance(curve, str):
            curve = CurveType(curve)

        self._segments.append(Segment(
            start_beat=self._current_beat,
            end_beat=beat,
            start_value=self._current_value,
            end_value=value,
            curve=curve,
        ))
        self._current_beat = beat
        self._current_value = value
        return self

    def at(self, beat: float, value: float) -> AutomationBuilder:
        """
        Set the starting position for subsequent .to() calls.

        This doesn't create a segment, just sets the reference point.
        """
        self._current_beat = beat
        self._current_value = value
        return self

    def loop(self, beats: float) -> AutomationBuilder:
        """Make the automation loop every N beats."""
        self._loop_beats = beats
        return self

    def build(self) -> Automation:
        """Build the final Automation object."""
        return Automation(
            segments=list(self._segments),
            loop_beats=self._loop_beats,
        )

    # Allow using builder directly where Automation is expected
    def get_value(self, beat: float) -> float | None:
        """Delegate to built automation."""
        return self.build().get_value(beat)

    def get_value_or_default(self, beat: float, default: float = 1.0) -> float:
        """Delegate to built automation."""
        return self.build().get_value_or_default(beat, default)


# ============================================================================
# CONVENIENCE CONSTRUCTORS
# ============================================================================

def automation() -> AutomationBuilder:
    """Create a new automation builder."""
    return AutomationBuilder()


def ramp(
    start_beat: float,
    end_beat: float,
    start_value: float = 0.0,
    end_value: float = 1.0,
    curve: str | CurveType = CurveType.LINEAR,
) -> Automation:
    """
    Create a simple ramp automation.

    Example:
        pattern.brightness(ramp(0, 1, 0.0, 1.0))  # Fade in over beat 0-1
        pattern.brightness(ramp(0, 4, 1.0, 0.0, "ease_out"))  # Slow fade out
    """
    if isinstance(curve, str):
        curve = CurveType(curve)

    return Automation([Segment(
        start_beat=start_beat,
        end_beat=end_beat,
        start_value=start_value,
        end_value=end_value,
        curve=curve,
    )])


def hold(start_beat: float, end_beat: float, value: float = 1.0) -> Automation:
    """
    Create a constant-value automation.

    Example:
        pattern.brightness(hold(0, 4, 0.5))  # 50% brightness for 4 beats
    """
    return Automation([Segment(
        start_beat=start_beat,
        end_beat=end_beat,
        start_value=value,
        end_value=value,
        curve=CurveType.HOLD,
    )])


def keyframes(
    points: list[tuple[float, float]],
    curve: str | CurveType = CurveType.LINEAR,
    loop: bool = False,
) -> Automation:
    """
    Create automation from a list of (beat, value) keyframes.

    Linear interpolation between points by default.

    Example:
        pattern.brightness(keyframes([
            (0, 0.0),    # Beat 0: 0%
            (1, 1.0),    # Beat 1: 100%
            (2, 1.0),    # Beat 2: 100% (hold)
            (4, 0.0),    # Beat 4: 0%
        ]))
    """
    if isinstance(curve, str):
        curve = CurveType(curve)

    if len(points) < 2:
        if len(points) == 1:
            beat, value = points[0]
            return hold(beat, beat + 1, value)
        return Automation()

    segments = []
    for i in range(len(points) - 1):
        start_beat, start_value = points[i]
        end_beat, end_value = points[i + 1]

        # If values are the same, use hold curve
        seg_curve = CurveType.HOLD if start_value == end_value else curve

        segments.append(Segment(
            start_beat=start_beat,
            end_beat=end_beat,
            start_value=start_value,
            end_value=end_value,
            curve=seg_curve,
        ))

    loop_beats = points[-1][0] - points[0][0] if loop else None
    return Automation(segments=segments, loop_beats=loop_beats)


def triangle(
    beats: float = 4.0,
    min_value: float = 0.0,
    max_value: float = 1.0,
    loop: bool = True,
) -> Automation:
    """
    Create a triangle wave automation (linear up and down).

    Example:
        pattern.brightness(triangle(beats=4))  # 4-beat triangle wave
    """
    half = beats / 2
    return Automation(
        segments=[
            Segment(0, half, min_value, max_value, CurveType.LINEAR),
            Segment(half, beats, max_value, min_value, CurveType.LINEAR),
        ],
        loop_beats=beats if loop else None,
    )


def sawtooth(
    beats: float = 4.0,
    min_value: float = 0.0,
    max_value: float = 1.0,
    loop: bool = True,
) -> Automation:
    """
    Create a sawtooth wave automation (ramp up, instant reset).

    Example:
        pattern.brightness(sawtooth(beats=1))  # Ramp up every beat
    """
    return Automation(
        segments=[
            Segment(0, beats, min_value, max_value, CurveType.LINEAR),
        ],
        loop_beats=beats if loop else None,
    )


def pulse(
    beats: float = 1.0,
    on_duration: float = 0.25,
    min_value: float = 0.0,
    max_value: float = 1.0,
    loop: bool = True,
) -> Automation:
    """
    Create a pulse/gate automation (on for on_duration, off for rest).

    Example:
        pattern.brightness(pulse(beats=1, on_duration=0.25))  # 25% duty cycle
    """
    return Automation(
        segments=[
            Segment(0, on_duration, max_value, max_value, CurveType.HOLD),
            Segment(on_duration, beats, min_value, min_value, CurveType.HOLD),
        ],
        loop_beats=beats if loop else None,
    )


def sine_wave(
    beats: float = 4.0,
    min_value: float = 0.0,
    max_value: float = 1.0,
    loop: bool = True,
    resolution: int = 16,
) -> Automation:
    """
    Create a sine wave automation.

    Uses multiple segments to approximate a sine wave.

    Example:
        pattern.brightness(sine_wave(beats=4))  # 4-beat sine wave
    """
    segments = []
    step = beats / resolution

    for i in range(resolution):
        start_beat = i * step
        end_beat = (i + 1) * step

        # Calculate sine values (0-1 range)
        start_t = (i / resolution) * 2 * math.pi
        end_t = ((i + 1) / resolution) * 2 * math.pi

        start_sine = (math.sin(start_t - math.pi / 2) + 1) / 2
        end_sine = (math.sin(end_t - math.pi / 2) + 1) / 2

        # Scale to min/max range
        start_value = min_value + (max_value - min_value) * start_sine
        end_value = min_value + (max_value - min_value) * end_sine

        segments.append(Segment(
            start_beat=start_beat,
            end_beat=end_beat,
            start_value=start_value,
            end_value=end_value,
            curve=CurveType.LINEAR,
        ))

    return Automation(
        segments=segments,
        loop_beats=beats if loop else None,
    )


# Type alias for automation or builder
AutomationType = Automation | AutomationBuilder
