"""
LightPattern class - the core composable pattern type.

A LightPattern wraps a query function and provides chainable
transformation methods. All transforms return new patterns (immutable).
"""

from __future__ import annotations

import random
from fractions import Fraction
from typing import Callable

from .types import TimeSpan, LightHap, LightValue, LightContext, HSV
from .envelope import Envelope
from ..modulator import Modulator, WaveType
from ..color import resolve_color


# Type alias for query functions
QueryFunc = Callable[[TimeSpan, LightContext], list[LightHap]]


class LightPattern:
    """
    A composable pattern that generates lighting events.

    Patterns are functions from (TimeSpan, LightContext) -> list[LightHap].
    All transformations return new patterns (immutable/functional style).

    Example:
        pattern = light("all").seq().shuffle().fast(2).color("red")
        haps = pattern.query(TimeSpan(0, 1), context)
    """

    def __init__(self, query_func: QueryFunc):
        """
        Initialize with a query function.

        Args:
            query_func: Function that takes (TimeSpan, LightContext) and returns LightHaps
        """
        self._query = query_func

    def query(self, span: TimeSpan, context: LightContext) -> list[LightHap]:
        """Query events within the given time span."""
        return self._query(span, context)

    def query_cycle(self, cycle: int, context: LightContext) -> list[LightHap]:
        """Convenience: query a complete cycle."""
        return self.query(TimeSpan(Fraction(cycle), Fraction(cycle + 1)), context)

    # =========================================================================
    # TIME TRANSFORMATIONS
    # =========================================================================

    def fast(self, factor: float | int) -> LightPattern:
        """
        Speed up pattern by factor.

        fast(2) = pattern plays twice as fast (2x per cycle)
        """
        factor_frac = Fraction(factor).limit_denominator(1000)

        def query_fast(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            # Query a larger time span, then compress results
            expanded = TimeSpan(span.start * factor_frac, span.end * factor_frac)
            haps = self._query(expanded, ctx)
            return [h.scale(factor_frac) for h in haps]

        return LightPattern(query_fast)

    def slow(self, factor: float | int) -> LightPattern:
        """
        Slow down pattern by factor.

        slow(2) = pattern plays at half speed (takes 2 cycles)
        """
        return self.fast(Fraction(1, factor) if isinstance(factor, int) else 1 / factor)

    def early(self, offset: float) -> LightPattern:
        """Shift pattern earlier in time by offset cycles."""
        offset_frac = Fraction(offset).limit_denominator(1000)

        def query_early(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            shifted_span = span.shift(offset_frac)
            haps = self._query(shifted_span, ctx)
            return [h.shift(-offset_frac) for h in haps]

        return LightPattern(query_early)

    def late(self, offset: float) -> LightPattern:
        """Shift pattern later in time by offset cycles."""
        return self.early(-offset)

    # =========================================================================
    # STRUCTURAL TRANSFORMATIONS
    # =========================================================================

    def seq(self, slots: int | None = None, per_group: bool = True) -> LightPattern:
        """
        Convert group references to sequences through individual lights.

        light("all").seq() -> sequences through each physical group (strip, lamps)
        light("all").seq(slots=16) -> sequence with 16th note timing (16 slots per cycle)
        light("all").seq(per_group=False) -> sequence through ALL lights together

        Args:
            slots: Optional total number of slots per cycle. If provided, each light
                   gets one slot (1/slots of the cycle), and remaining slots are empty.
                   This enables 16th note timing: seq(slots=16) gives each light 1/16 cycle.
            per_group: If True (default), when targeting "all", run the sequence
                       within each physical group (strip, lamps) simultaneously.
                       If False, sequence through all lights together.
        """
        def query_seq(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            for hap in haps:
                # If this hap references a group, expand it to individual lights
                if hap.value.group and hap.value.light_id is None:
                    group_name = hap.value.group

                    # Check if we should run per physical group
                    # Only do this for "all" group when strip/lamps exist
                    if per_group and group_name == "all":
                        strip = ctx.resolve_group("strip")
                        lamps = ctx.resolve_group("lamps")

                        # If we have both strip and lamps, run sequence in each
                        if strip and lamps:
                            physical_groups = [strip, lamps]
                        elif strip:
                            physical_groups = [strip]
                        elif lamps:
                            physical_groups = [lamps]
                        else:
                            # No physical groups, fall back to all lights
                            physical_groups = [ctx.resolve_group("all")]
                    else:
                        # Single group - just use its lights
                        physical_groups = [ctx.resolve_group(group_name)]

                    # Generate sequence for each physical group
                    event_span = hap.whole_or_part()
                    event_duration = event_span.duration

                    for lights in physical_groups:
                        if not lights:
                            continue

                        n = len(lights)

                        # If slots specified, each light gets 1/slots of the event
                        # Scale slots proportionally for smaller groups
                        if slots is not None:
                            # Scale slots based on group size ratio
                            group_slots = max(n, slots * n // ctx.num_lights)
                            num_slots = group_slots
                        else:
                            # Use quarter notes (4 slots per bar) minimum
                            # Lights wrap around modulo-style for polyrhythmic phasing
                            num_slots = max(4, n)
                            # Round up to power of 2 if we have more lights than 4
                            if n > 4:
                                num_slots = 4
                                while num_slots < n:
                                    num_slots *= 2

                        light_duration = event_duration / num_slots

                        # For continuous polyrhythmic phasing, calculate the absolute
                        # slot position based on time, not relative to event start.
                        # This makes the light sequence continue across bars.
                        # With 3 lights and 4 slots/bar:
                        #   Bar 1: lights 0,1,2,0  Bar 2: lights 1,2,0,1  Bar 3: lights 2,0,1,2
                        cycle_start = int(event_span.start)  # Which cycle/bar we're in
                        base_slot = (cycle_start * num_slots) % n  # Accumulated offset

                        # Generate events for each slot, wrapping light indices
                        for slot in range(num_slots):
                            light_id = lights[(base_slot + slot) % n]  # Wrap with phase offset
                            light_start = event_span.start + light_duration * slot
                            light_end = light_start + light_duration
                            light_whole = TimeSpan(light_start, light_end)

                            # Intersect with query span
                            intersection = light_whole.intersection(span)
                            if intersection:
                                new_value = LightValue(
                                    light_id=light_id,
                                    group=None,
                                    color=hap.value.color,
                                    intensity=hap.value.intensity,
                                    envelope=hap.value.envelope,
                                    modulator=hap.value.modulator,
                                )
                                result.append(LightHap(
                                    whole=light_whole,
                                    part=intersection,
                                    value=new_value,
                                ))
                else:
                    result.append(hap)

            return result

        return LightPattern(query_seq)

    def shuffle(self, seed: int | None = None) -> LightPattern:
        """
        Shuffle event order within each cycle.

        The shuffle is deterministic per cycle (same shuffle for same cycle number).
        Works correctly with partial queries by computing full-cycle permutation first.
        """
        def query_shuffle(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            # Query the full cycle(s) to get all events for proper shuffling
            cycle_start = int(span.start)
            cycle_end = int(span.end) + 1

            result = []
            for cycle in range(cycle_start, cycle_end):
                # Query this complete cycle
                full_cycle_span = TimeSpan(Fraction(cycle), Fraction(cycle + 1))
                cycle_haps = self._query(full_cycle_span, ctx)

                if len(cycle_haps) <= 1:
                    # Filter to original span
                    for h in cycle_haps:
                        intersection = h.part.intersection(span)
                        if intersection:
                            result.append(h.with_part(intersection))
                    continue

                # Deterministic shuffle based on cycle number
                rng = random.Random(cycle if seed is None else seed + cycle)

                # Sort haps by time to ensure consistent ordering before shuffle
                cycle_haps.sort(key=lambda h: (h.whole_or_part().start, h.value.light_id or 0))

                # Extract timing and values separately
                timings = [(h.whole, h.part) for h in cycle_haps]
                values = [h.value for h in cycle_haps]

                # Shuffle values, keep timings in place
                rng.shuffle(values)

                # Rebuild haps and filter to original query span
                for (whole, part), value in zip(timings, values):
                    intersection = part.intersection(span)
                    if intersection:
                        result.append(LightHap(whole=whole, part=intersection, value=value))

            return result

        return LightPattern(query_shuffle)

    def rev(self) -> LightPattern:
        """Reverse pattern within each cycle."""
        def query_rev(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            for h in haps:
                cycle = int(h.part.start)
                cycle_start = Fraction(cycle)

                # Mirror times around cycle center
                def mirror(t: Fraction) -> Fraction:
                    return cycle_start + (Fraction(1) - (t - cycle_start))

                new_whole = None
                if h.whole:
                    new_whole = TimeSpan(mirror(h.whole.end), mirror(h.whole.start))

                new_part = TimeSpan(mirror(h.part.end), mirror(h.part.start))
                result.append(LightHap(whole=new_whole, part=new_part, value=h.value))

            return result

        return LightPattern(query_rev)

    def autonomous(
        self,
        min_on: int = 1,
        max_on: int = 4,
        min_off: int = 1,
        max_off: int = 2,
        colors: list[str] | None = None,
        seed: int | None = None,
    ) -> LightPattern:
        """
        Make each light behave autonomously with random on/off timing.

        Each light independently turns on and off at beat-quantized intervals.
        The timing is pseudo-random but deterministic (same seed = same pattern).
        Lights turn on/off instantly (no fading).

        Args:
            min_on: Minimum beats to stay on (default 1)
            max_on: Maximum beats to stay on (default 4)
            min_off: Minimum beats to stay off (default 1)
            max_off: Maximum beats to stay off (default 2)
            colors: Optional list of color names to randomly choose from per event
            seed: Random seed for reproducibility (default: uses light_id)

        Example:
            # Each light randomly on 1-4 beats, off 1-2 beats
            light("all").autonomous(min_on=1, max_on=4, min_off=1, max_off=2)

            # With random colors from a palette
            light("all").autonomous(min_on=2, max_on=6, colors=["yellow", "orange", "amber"])
        """
        # Pre-resolve colors if provided
        resolved_colors = None
        if colors:
            resolved_colors = [resolve_color(c) for c in colors]

        def query_autonomous(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            # Group haps by light_id to process each light independently
            # First, resolve any group references to individual lights
            resolved_haps: dict[int, LightValue] = {}
            for hap in haps:
                if hap.value.light_id is not None:
                    resolved_haps[hap.value.light_id] = hap.value
                elif hap.value.group:
                    for light_id in ctx.resolve_group(hap.value.group):
                        # Create a value for this specific light
                        resolved_haps[light_id] = LightValue(
                            light_id=light_id,
                            group=None,
                            color=hap.value.color,
                            intensity=hap.value.intensity,
                            envelope=hap.value.envelope,
                            modulator=hap.value.modulator,
                        )

            # For each light, generate its autonomous on/off pattern
            # We need to look back far enough to know current state
            lookback_beats = (max_on + max_off) * 4  # Conservative lookback
            cycle_beats = int(ctx.cycle_beats)

            for light_id, base_value in resolved_haps.items():
                # Each light gets its own RNG seeded by light_id
                light_seed = (seed if seed is not None else 0) + light_id * 1000
                rng = random.Random(light_seed)

                # Generate pattern from well before the query span
                # Start from a deterministic point (beat 0 of some early cycle)
                start_beat = max(0, int(float(span.start) * cycle_beats) - lookback_beats)
                end_beat = int(float(span.end) * cycle_beats) + cycle_beats

                # Reset RNG to start_beat state by advancing from 0
                rng = random.Random(light_seed)
                current_beat = 0

                # Fast-forward RNG state to start_beat
                while current_beat < start_beat:
                    is_on = rng.random() < 0.5  # Initial state
                    if is_on:
                        duration = rng.randint(min_on, max_on)
                        if resolved_colors:
                            rng.choice(resolved_colors)  # Consume RNG state
                    else:
                        duration = rng.randint(min_off, max_off)
                    current_beat += duration

                # Now generate events in the query range
                # Re-seed and regenerate to get proper state
                rng = random.Random(light_seed)
                current_beat = 0
                is_on = rng.random() < 0.5  # Initial state at beat 0

                while current_beat < end_beat:
                    if is_on:
                        duration = rng.randint(min_on, max_on)

                        # Pick a random color if palette provided
                        if resolved_colors:
                            event_color = rng.choice(resolved_colors)
                            event_value = base_value.with_color(event_color)
                        else:
                            event_value = base_value

                        # This is an ON period - create an event
                        event_start_cycle = Fraction(current_beat, cycle_beats)
                        event_end_cycle = Fraction(current_beat + duration, cycle_beats)
                        event_span = TimeSpan(event_start_cycle, event_end_cycle)

                        # Check if this event overlaps with query span
                        intersection = event_span.intersection(span)
                        if intersection:
                            result.append(LightHap(
                                whole=event_span,
                                part=intersection,
                                value=event_value,
                            ))
                    else:
                        duration = rng.randint(min_off, max_off)
                        # OFF period - no event generated

                    current_beat += duration
                    is_on = not is_on  # Toggle state

            return result

        return LightPattern(query_autonomous)

    # =========================================================================
    # VALUE TRANSFORMATIONS
    # =========================================================================

    def color(
        self,
        color: HSV | str | None = None,
        *,
        flash: HSV | str | None = None,
        fade: HSV | str | None = None,
    ) -> LightPattern:
        """
        Set color properties.

        Args:
            color: Base color for all events
            flash: Color during envelope attack phase
            fade: Color during envelope decay/sustain phase
        """
        base_color = resolve_color(color)
        flash_color = resolve_color(flash)
        fade_color = resolve_color(fade)

        def query_color(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            for h in haps:
                new_value = h.value
                if base_color:
                    new_value = new_value.with_color(base_color)

                # Apply flash/fade colors to envelope
                if flash_color or fade_color:
                    env = new_value.envelope or Envelope()
                    env = env.with_colors(flash=flash_color, fade=fade_color)
                    new_value = new_value.with_envelope(env)

                result.append(h.with_value(new_value))

            return result

        return LightPattern(query_color)

    def intensity(self, value: float) -> LightPattern:
        """Set base intensity (0.0-1.0)."""
        def query_intensity(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            return [h.with_value(h.value.with_intensity(value)) for h in haps]

        return LightPattern(query_intensity)

    def envelope(
        self,
        attack: float = 0.0,
        decay: float = 0.0,
        sustain: float = 1.0,
        release: float = 0.0,
        *,
        fade: float | None = None,
    ) -> LightPattern:
        """
        Apply an ADSR-style envelope to events.

        Args:
            attack: Attack time (cycles) - ramp up to peak
            decay: Decay time (cycles) - ramp down to sustain level
            sustain: Sustain level (0.0-1.0)
            release: Release time (cycles) - ramp to zero after event
            fade: Shorthand for decay (if set, decay=fade)
        """
        if fade is not None:
            decay = fade

        env = Envelope(
            attack=attack,
            decay=decay,
            sustain=sustain,
            release=release,
        )

        def query_envelope(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            for h in haps:
                # Merge with existing envelope
                existing = h.value.envelope
                merged = env.merge(existing) if existing else env
                new_value = h.value.with_envelope(merged)
                result.append(h.with_value(new_value))

            return result

        return LightPattern(query_envelope)

    def modulate(
        self,
        wave: str = "sine",
        frequency: float = 1.0,
        min_intensity: float = 0.0,
        max_intensity: float = 1.0,
        phase: float = 0.0,
    ) -> LightPattern:
        """
        Apply oscillating intensity modulation to events.

        The modulation is based on absolute bar position, not event-relative
        time. This means all events in a bar share the same modulation phase,
        creating coherent visual effects.

        Args:
            wave: Waveform type ("sine", "triangle", "saw", "square")
            frequency: Oscillations per bar (1.0 = one cycle per bar)
            min_intensity: Minimum intensity (0.0-1.0)
            max_intensity: Maximum intensity (0.0-1.0)
            phase: Phase offset in cycles (0.0-1.0)

        Examples:
            # Gentle breathing between 80% and 100% over each bar
            .modulate("sine", frequency=1.0, min_intensity=0.8, max_intensity=1.0)

            # Fast pulsing 4x per bar
            .modulate("square", frequency=4.0, min_intensity=0.5, max_intensity=1.0)

            # Slow 2-bar breathe
            .modulate("sine", frequency=0.5, min_intensity=0.6, max_intensity=1.0)

        Returns:
            New LightPattern with modulation applied
        """
        wave_type = WaveType(wave.lower())

        mod = Modulator(
            wave=wave_type,
            frequency=frequency,
            min_intensity=min_intensity,
            max_intensity=max_intensity,
            phase=phase,
        )

        def query_modulate(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            for h in haps:
                new_value = h.value.with_modulator(mod)
                result.append(h.with_value(new_value))

            return result

        return LightPattern(query_modulate)

    # =========================================================================
    # ZONE TARGETING
    # =========================================================================

    def zone(
        self,
        target_zone: str,
        fallback: str | None = None,
    ) -> LightPattern:
        """
        Restrict pattern to a specific zone.

        Filters events to only include lights that belong to the target zone.
        If the zone doesn't exist, optionally falls back to another zone,
        or returns no events (black).

        Args:
            target_zone: Zone name ("ceiling", "perimeter", or custom)
            fallback: Fallback zone if target unavailable (or "all" for all lights)

        Examples:
            # Strobe only on ceiling lights
            strobe().zone("ceiling")

            # Chase on perimeter, with fallback to all lights if no perimeter
            chase().zone("perimeter", fallback="all")

            # Combine zones with stack
            stack(
                strobe().fast(4).zone("ceiling"),
                pulse().slow(2).zone("perimeter"),
            )

            # Zone transforms compose with other transforms
            light("all").seq().zone("ceiling").fast(2).color("cyan")
        """
        def query_zone(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            # Determine which lights are in the target zone
            if ctx.has_zone(target_zone):
                zone_lights = set(ctx.resolve_zone(target_zone))
            elif fallback:
                # Try fallback zone
                if fallback == "all":
                    zone_lights = set(range(ctx.num_lights))
                elif ctx.has_zone(fallback):
                    zone_lights = set(ctx.resolve_zone(fallback))
                else:
                    # Fallback zone also doesn't exist
                    return []
            else:
                # No fallback, zone unavailable
                return []

            if not zone_lights:
                return []

            # Query underlying pattern
            haps = self._query(span, ctx)

            # Filter/expand to zone lights only
            result = []
            for hap in haps:
                if hap.value.light_id is not None:
                    # Individual light - check if in zone
                    if hap.value.light_id in zone_lights:
                        result.append(hap)
                elif hap.value.group:
                    # Group reference - expand and intersect with zone
                    group_lights = set(ctx.resolve_group(hap.value.group))
                    intersected = group_lights & zone_lights
                    for light_id in intersected:
                        result.append(hap.with_value(LightValue(
                            light_id=light_id,
                            group=None,
                            color=hap.value.color,
                            intensity=hap.value.intensity,
                            envelope=hap.value.envelope,
                            modulator=hap.value.modulator,
                        )))

            return result

        return LightPattern(query_zone)

    # =========================================================================
    # COMBINATION
    # =========================================================================

    def __add__(self, other: LightPattern) -> LightPattern:
        """Combine two patterns (overlay). Use stack() for more than two."""
        def query_add(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            return self._query(span, ctx) + other._query(span, ctx)

        return LightPattern(query_add)

    def __repr__(self) -> str:
        return f"LightPattern({self._query})"
