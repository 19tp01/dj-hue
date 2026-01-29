"""
Pattern scheduler for the Strudel pattern system.

Bridges the pattern system with the render loop, converting
pattern queries into RGB colors for each light.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING

from .core.types import TimeSpan, LightHap, LightContext, HSV
from .core.pattern import LightPattern
from .core.envelope import Envelope
from .palette import Palette, PaletteRef

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
        palette: Palette | None = None,
    ):
        """
        Initialize the scheduler.

        Args:
            pattern: The LightPattern to render
            context: Light context (num_lights, groups)
            default_color: Default color when none specified
            cycle_beats: Beats per cycle (default 4 for 4/4 time)
            palette: Active color palette for resolving PaletteRef colors
        """
        self.pattern = pattern
        self.context = context
        self.default_color = default_color or HSV(0.0, 1.0, 1.0)  # Red default
        self.cycle_beats = cycle_beats
        self.palette = palette

        # Track active events for long envelopes
        self._active_events: dict[int, ActiveEvent] = {}

    def set_palette(self, palette: Palette | None) -> None:
        """Update the active palette for color resolution."""
        self.palette = palette

    def _resolve_color(
        self,
        color: HSV | None,
        color_ref: PaletteRef | None,
        event_index: int,
        cycle_position: Fraction,
    ) -> HSV:
        """
        Resolve a color, handling both literal HSV and PaletteRef.

        Args:
            color: Literal HSV color (takes precedence)
            color_ref: Palette reference for deferred resolution
            event_index: Index of this event (for CYCLE mode)
            cycle_position: Current cycle position (for RANDOM seeding)

        Returns:
            Resolved HSV color, or default_color if unable to resolve
        """
        # Literal color takes precedence
        if color is not None:
            return color

        # Try to resolve palette reference
        if color_ref is not None and self.palette is not None:
            return color_ref.resolve(
                palette=self.palette,
                event_index=event_index,
                cycle_position=cycle_position,
            )

        # Fallback to default
        return self.default_color

    def _get_envelope_color(
        self,
        envelope: Envelope,
        time_in_event: float,
        base_color: HSV,
        event_index: int,
        cycle_position: Fraction,
    ) -> HSV:
        """
        Get color from envelope, resolving any palette references.

        Handles flash/fade color resolution with palette support.
        """
        from .core.envelope import interpolate_hsv

        # Resolve flash color (literal or palette ref)
        flash_color = envelope.flash_color
        if flash_color is None and envelope.flash_ref is not None and self.palette is not None:
            flash_color = envelope.flash_ref.resolve(
                palette=self.palette,
                event_index=event_index,
                cycle_position=cycle_position,
            )

        # Resolve fade color (literal or palette ref)
        fade_color = envelope.fade_color
        if fade_color is None and envelope.fade_ref is not None and self.palette is not None:
            fade_color = envelope.fade_ref.resolve(
                palette=self.palette,
                event_index=event_index,
                cycle_position=cycle_position,
            )

        # During attack phase, use flash color if available
        if time_in_event < envelope.attack:
            if flash_color:
                return flash_color
            if fade_color:
                return fade_color
            return base_color

        # After attack, use fade color or interpolate
        if fade_color:
            if flash_color and envelope.decay > 0:
                # Interpolate from flash to fade during decay
                time_after_attack = time_in_event - envelope.attack
                if time_after_attack < envelope.decay:
                    t = time_after_attack / envelope.decay
                    return interpolate_hsv(flash_color, fade_color, t)
            return fade_color

        if flash_color:
            return flash_color

        return base_color

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

        # Query a window around current time
        # Margin needs to be large enough to catch fast events at 50Hz render rate
        # At 120 BPM, 1 cycle = 2 sec, 50Hz = 20ms/frame = 0.01 cycles/frame
        # Use 0.02 margin (0.04 total window) for safety with fast patterns
        query_margin = Fraction(1, 50)
        query_start = max(Fraction(0), cycle_position - query_margin)
        query_end = cycle_position + query_margin
        query_span = TimeSpan(query_start, query_end)

        haps = self.pattern.query(query_span, self.context)

        # Build light state - track intensity to implement HTP (Highest Takes Precedence)
        colors: dict[int, RGB] = {}
        intensities: dict[int, float] = {}  # Track intensity for HTP blending

        # First, check currently active events from the query
        for hap_idx, hap in enumerate(haps):
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

                    # Get base color (resolving palette ref if needed)
                    base_color = self._resolve_color(
                        hap.value.color,
                        hap.value.color_ref,
                        event_index=hap_idx,
                        cycle_position=cycle_position,
                    )

                    # Apply envelope if present
                    envelope = hap.value.envelope
                    if envelope:
                        envelope_intensity = envelope.get_intensity(time_in_event)
                        # Resolve envelope colors (flash/fade) with palette support
                        color = self._get_envelope_color(
                            envelope, time_in_event, base_color, hap_idx, cycle_position
                        )
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

                    # Skip rendering if intensity is below perceptible threshold
                    # This prevents color artifacts when envelope decays to near-zero
                    if intensity < 0.01:
                        continue

                    # HTP (Highest Takes Precedence) - only update if brighter
                    if light_id not in intensities or intensity > intensities[light_id]:
                        colors[light_id] = RGB.from_hsv(color.hue, color.saturation, intensity)
                        intensities[light_id] = intensity

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
                # Resolve base color (using light_id as stable event index for active events)
                base_color = self._resolve_color(
                    active.hap.value.color,
                    active.hap.value.color_ref,
                    event_index=light_id,  # Use light_id for consistent color during envelope
                    cycle_position=cycle_position,
                )
                envelope_intensity = envelope.get_intensity(time_since_event_start)
                # Resolve envelope colors with palette support
                color = self._get_envelope_color(
                    envelope, time_since_event_start, base_color, light_id, cycle_position
                )

                # Apply modulator if present (uses absolute cycle position)
                modulator = active.hap.value.modulator
                if modulator:
                    modulator_intensity = modulator.get_intensity(current_time)
                else:
                    modulator_intensity = 1.0

                intensity = active.hap.value.intensity * envelope_intensity * modulator_intensity

                # Skip rendering if intensity is below perceptible threshold
                if intensity < 0.01:
                    expired_events.append(light_id)
                    continue

                # HTP (Highest Takes Precedence) - only update if brighter
                if light_id not in intensities or intensity > intensities[light_id]:
                    colors[light_id] = RGB.from_hsv(color.hue, color.saturation, intensity)
                    intensities[light_id] = intensity
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
    default_palette_name: str | None = None

    _scheduler: PatternScheduler | None = field(default=None, repr=False)
    _palette: Palette | None = field(default=None, repr=False)

    def get_scheduler(self, context: LightContext) -> PatternScheduler:
        """Get or create the scheduler for this pattern."""
        if self._scheduler is None or self._scheduler.context != context:
            self._scheduler = PatternScheduler(
                pattern=self.pattern,
                context=context,
                default_color=self.default_color,
                palette=self._palette,
            )
        return self._scheduler

    def set_palette(self, palette: Palette | None) -> None:
        """Set the active palette for color resolution."""
        self._palette = palette
        if self._scheduler:
            self._scheduler.set_palette(palette)

    def compute_colors(
        self,
        beat_position: float,
        context: LightContext,
    ) -> dict[int, "RGB"]:
        """Compute colors - drop-in for Pattern rendering."""
        scheduler = self.get_scheduler(context)
        return scheduler.compute_colors(beat_position)
