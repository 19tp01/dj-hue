"""
Pattern scheduler for the Strudel pattern system.

Bridges the pattern system with the render loop, converting
pattern queries into RGB colors for each light.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING

from .core import TimeSpan, LightHap, LightContext
from .pattern import LightPattern
from .envelope import Envelope
from ..pattern_def import HSV

if TYPE_CHECKING:
    from ...lights.effects import RGB


@dataclass
class ActiveEvent:
    """Tracks an event that's currently active (for envelope continuation)."""
    hap: LightHap
    start_cycle: float  # When this event started (in cycles)


class PatternScheduler:
    """
    Schedules pattern queries and renders to light colors.

    Integrates with the existing render loop by providing a
    compute_colors() method that returns RGB values for each light.
    """

    def __init__(
        self,
        pattern: LightPattern,
        context: LightContext,
        default_color: HSV | None = None,
        cycle_beats: float = 4.0,
    ):
        """
        Initialize the scheduler.

        Args:
            pattern: The LightPattern to render
            context: Light context (num_lights, groups)
            default_color: Default color when none specified
            cycle_beats: Beats per cycle (default 4 for 4/4 time)
        """
        self.pattern = pattern
        self.context = context
        self.default_color = default_color or HSV(0.0, 1.0, 1.0)  # Red default
        self.cycle_beats = cycle_beats

        # Track active events for long envelopes
        self._active_events: dict[int, ActiveEvent] = {}

    def compute_colors(self, beat_position: float) -> dict[int, "RGB"]:
        """
        Compute RGB colors for all lights at the current beat position.

        This is called every frame (~50Hz) by the render loop.

        Args:
            beat_position: Current beat position (e.g., 4.5 = halfway through beat 5)

        Returns:
            Dict mapping light_id to RGB color
        """
        from ...lights.effects import RGB

        # Convert beat position to cycle position
        cycle_position = Fraction(beat_position) / Fraction(self.cycle_beats)
        current_time = float(cycle_position)

        # Query a small window around current time
        query_margin = Fraction(1, 100)
        query_start = max(Fraction(0), cycle_position - query_margin)
        query_end = cycle_position + query_margin
        query_span = TimeSpan(query_start, query_end)

        haps = self.pattern.query(query_span, self.context)

        # Build light state
        colors: dict[int, RGB] = {}

        # First, check currently active events from the query
        for hap in haps:
            # Resolve light_id(s) for this hap
            if hap.value.light_id is not None:
                light_ids = [hap.value.light_id]
            elif hap.value.group:
                light_ids = self.context.resolve_group(hap.value.group)
            else:
                continue

            for light_id in light_ids:
                if light_id < 0 or light_id >= self.context.num_lights:
                    continue

                # Calculate phase within this event
                event_span = hap.whole_or_part()
                event_start = float(event_span.start)

                # Is this event currently active?
                if event_span.contains(cycle_position):
                    time_in_event = current_time - event_start

                    # Get base color
                    base_color = hap.value.color or self.default_color

                    # Apply envelope if present
                    envelope = hap.value.envelope
                    if envelope:
                        envelope_intensity = envelope.get_intensity(time_in_event)
                        color = envelope.get_color(time_in_event, base_color)
                    else:
                        envelope_intensity = 1.0
                        color = base_color

                    # Apply modulator if present (uses absolute cycle position)
                    modulator = hap.value.modulator
                    if modulator:
                        modulator_intensity = modulator.get_intensity(current_time)
                    else:
                        modulator_intensity = 1.0

                    intensity = hap.value.intensity * envelope_intensity * modulator_intensity

                    colors[light_id] = RGB.from_hsv(color.hue, color.saturation, intensity)

                    # Track for envelope continuation after event ends
                    self._active_events[light_id] = ActiveEvent(hap, event_start)

        # Second, check all tracked active events (even if not in current query)
        # This handles envelopes that extend beyond their event slot
        expired_events = []
        for light_id, active in self._active_events.items():
            # Skip if already computed from current query
            if light_id in colors:
                continue

            envelope = active.hap.value.envelope
            if not envelope:
                expired_events.append(light_id)
                continue

            active_span = active.hap.whole_or_part()
            time_since_event_start = current_time - float(active_span.start)

            # Calculate when the envelope actually ends (not just the event slot)
            # The envelope can extend beyond the event if decay > event duration
            envelope_end_time = float(active_span.start) + envelope.attack + envelope.decay

            # Stay active until the envelope is done (attack + decay complete)
            if current_time < envelope_end_time and time_since_event_start >= 0:
                base_color = active.hap.value.color or self.default_color
                envelope_intensity = envelope.get_intensity(time_since_event_start)
                color = envelope.get_color(time_since_event_start, base_color)

                # Apply modulator if present (uses absolute cycle position)
                modulator = active.hap.value.modulator
                if modulator:
                    modulator_intensity = modulator.get_intensity(current_time)
                else:
                    modulator_intensity = 1.0

                intensity = active.hap.value.intensity * envelope_intensity * modulator_intensity
                colors[light_id] = RGB.from_hsv(color.hue, color.saturation, intensity)
            else:
                # Envelope finished, mark for removal
                expired_events.append(light_id)

        # Clean up expired events
        for light_id in expired_events:
            del self._active_events[light_id]

        # Fill in missing lights with black
        for i in range(self.context.num_lights):
            if i not in colors:
                colors[i] = RGB.black()

        return colors

    def set_pattern(self, pattern: LightPattern) -> None:
        """Update the active pattern."""
        self.pattern = pattern
        self._active_events.clear()

    def set_context(self, context: LightContext) -> None:
        """Update the light context."""
        self.context = context
        self._active_events.clear()


@dataclass
class StrudelPatternWrapper:
    """
    Wrapper that makes a Strudel pattern compatible with PatternEngine.

    This allows gradual migration - Strudel patterns can coexist
    with the existing Pattern/GroupEffect system.
    """
    name: str
    pattern: LightPattern
    description: str = ""
    default_color: HSV = field(default_factory=lambda: HSV(0.0, 1.0, 1.0))

    _scheduler: PatternScheduler | None = field(default=None, repr=False)

    def get_scheduler(self, context: LightContext) -> PatternScheduler:
        """Get or create the scheduler for this pattern."""
        if self._scheduler is None or self._scheduler.context != context:
            self._scheduler = PatternScheduler(
                pattern=self.pattern,
                context=context,
                default_color=self.default_color,
            )
        return self._scheduler

    def compute_colors(
        self,
        beat_position: float,
        context: LightContext,
    ) -> dict[int, "RGB"]:
        """Compute colors - drop-in for Pattern rendering."""
        scheduler = self.get_scheduler(context)
        return scheduler.compute_colors(beat_position)
