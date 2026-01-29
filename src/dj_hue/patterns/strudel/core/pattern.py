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
from ..palette import PaletteRef


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
                    # Only do this for "all" group when physical zones exist
                    if per_group and group_name == "all":
                        strip = ctx.resolve_group("strip")
                        lamps = ctx.resolve_group("lamps")
                        ambient = ctx.resolve_group("ambient")

                        # Build list of physical groups (each sequences in parallel)
                        physical_groups = []
                        if strip:
                            physical_groups.append(strip)
                        if lamps:
                            physical_groups.append(lamps)
                        if ambient:
                            physical_groups.append(ambient)
                        if not physical_groups:
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

    def pick(
        self,
        min_n: int | float = 1,
        max_n: int | float | None = None,
        seed: int | None = None,
        hold: float | None = None,
    ) -> LightPattern:
        """
        Randomly pick N lights from each event's group.

        For each event that targets a group (like "all"), randomly selects
        between min_n and max_n lights. Deterministic per event timing.

        Args:
            min_n: Minimum lights to pick. Integer for absolute count, float 0.0-1.0 for percentage.
            max_n: Maximum lights to pick (default same as min_n). Same format as min_n.
            seed: Random seed for reproducibility
            hold: Hold the same random pick for this many cycles. For example, hold=0.25
                  keeps the same pick for 1 beat (quarter note). All events within the
                  same hold window share the same random selection.

        Example:
            # 1-2 random lights pop per beat
            light("all all all all").pick(1, 2).envelope(...)

            # Exactly 3 random lights per event
            light("all all").pick(3)

            # 20-50% of lights per event
            light("all all all all").pick(0.2, 0.5)

            # About half the lights
            light("all").pick(0.5)

            # Pick 1 light, hold for 1 beat (same light strobes within the beat)
            light("all").pick(1, hold=0.25).fast(16)
        """
        if max_n is None:
            max_n = min_n

        # Pre-convert hold to Fraction for efficiency
        hold_frac = Fraction(hold).limit_denominator(1000) if hold is not None else None

        def resolve_count(value: int | float, total: int) -> int:
            """Convert percentage (0.0-1.0) or absolute count to int."""
            if isinstance(value, float) and 0.0 <= value <= 1.0:
                return max(1, round(value * total))
            return int(value)

        def query_pick(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            for hap in haps:
                # If already targeting a specific light, keep it
                if hap.value.light_id is not None:
                    result.append(hap)
                    continue

                # Get lights from group
                if hap.value.group:
                    lights = ctx.resolve_group(hap.value.group)
                else:
                    lights = list(range(ctx.num_lights))

                if not lights:
                    continue

                # Resolve min/max based on group size
                actual_min = resolve_count(min_n, len(lights))
                actual_max = resolve_count(max_n, len(lights))

                # Deterministic random based on event timing
                event_time = hap.whole_or_part().start

                # If hold is set, quantize to hold intervals so events in
                # the same window share the same random pick
                if hold_frac is not None:
                    # Floor divide to get the hold window index
                    quantized_time = (event_time // hold_frac) * hold_frac
                    event_seed = (seed if seed is not None else 0) + hash(quantized_time)
                else:
                    event_seed = (seed if seed is not None else 0) + hash(event_time)

                rng = random.Random(event_seed)

                # Pick how many lights (clamped to available)
                n = rng.randint(actual_min, min(actual_max, len(lights)))
                n = max(1, min(n, len(lights)))

                # Randomly select n lights
                selected = rng.sample(lights, n)

                # Create a hap for each selected light
                for light_id in selected:
                    new_value = LightValue(
                        light_id=light_id,
                        group=None,
                        color=hap.value.color,
                        intensity=hap.value.intensity,
                        envelope=hap.value.envelope,
                        modulator=hap.value.modulator,
                    )
                    result.append(LightHap(
                        whole=hap.whole,
                        part=hap.part,
                        value=new_value,
                    ))

            return result

        return LightPattern(query_pick)

    def autonomous(
        self,
        min_freq: float = 1.0,
        max_freq: float = 4.0,
        duty: float = 0.5,
        colors: list[str] | None = None,
        seed: int | None = None,
    ) -> LightPattern:
        """
        Make each light behave autonomously with random frequency blinking.

        Each light independently blinks at a random frequency within the given range.
        The timing is pseudo-random but deterministic (same seed = same pattern).

        Args:
            min_freq: Minimum blinks per cycle/bar (default 1.0)
            max_freq: Maximum blinks per cycle/bar (default 4.0)
            duty: Duty cycle - fraction of time "on" (0.0-1.0, default 0.5)
            colors: Optional list of color names to randomly choose from per blink
            seed: Random seed for reproducibility (default: uses light_id)

        Example:
            # Each light blinks 1-4 times per bar
            light("all").autonomous(min_freq=1, max_freq=4)

            # Fast blinking 4-8 times per bar with short on-time
            light("all").autonomous(min_freq=4, max_freq=8, duty=0.3)

            # Slow ambient with random colors, mostly on
            light("all").autonomous(min_freq=0.5, max_freq=2, duty=0.8, colors=["red", "orange"])
        """
        # Pre-resolve colors if provided
        resolved_colors = None
        if colors:
            resolved_colors = [resolve_color(c) for c in colors]

        def query_autonomous(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            # Resolve any group references to individual lights
            resolved_haps: dict[int, LightValue] = {}
            for hap in haps:
                if hap.value.light_id is not None:
                    resolved_haps[hap.value.light_id] = hap.value
                elif hap.value.group:
                    for light_id in ctx.resolve_group(hap.value.group):
                        resolved_haps[light_id] = LightValue(
                            light_id=light_id,
                            group=None,
                            color=hap.value.color,
                            intensity=hap.value.intensity,
                            envelope=hap.value.envelope,
                            modulator=hap.value.modulator,
                        )

            # For each light, generate its autonomous blinking pattern
            for light_id, base_value in resolved_haps.items():
                # Each light gets its own RNG seeded by light_id
                light_seed = (seed if seed is not None else 0) + light_id * 1000
                rng = random.Random(light_seed)

                # Pick a random frequency for this light
                freq = rng.uniform(min_freq, max_freq)
                period = Fraction(1) / Fraction(freq).limit_denominator(1000)

                # Random phase offset (0 to 1 period)
                phase = Fraction(rng.random()).limit_denominator(1000) * period

                # Calculate on/off durations from duty cycle
                on_duration = period * Fraction(duty).limit_denominator(100)
                off_duration = period - on_duration

                # Generate events covering the query span
                # Start from before the span to catch events that overlap
                start_cycle = int(span.start) - 1
                end_cycle = int(span.end) + 2

                # Generate blinks from start_cycle
                current_time = Fraction(start_cycle) + phase
                blink_index = 0

                while current_time < span.end + period:
                    # ON period
                    on_start = current_time
                    on_end = current_time + on_duration
                    event_span = TimeSpan(on_start, on_end)

                    # Check if this event overlaps with query span
                    intersection = event_span.intersection(span)
                    if intersection:
                        # Pick color for this blink (deterministic per blink)
                        if resolved_colors:
                            # Use blink index for deterministic color selection
                            color_rng = random.Random(light_seed + blink_index)
                            event_color = color_rng.choice(resolved_colors)
                            event_value = base_value.with_color(event_color)
                        else:
                            event_value = base_value

                        result.append(LightHap(
                            whole=event_span,
                            part=intersection,
                            value=event_value,
                        ))

                    # Move to next blink
                    current_time += period
                    blink_index += 1

                    # Safety: don't generate too many events
                    if blink_index > 1000:
                        break

            return result

        return LightPattern(query_autonomous)

    # =========================================================================
    # VALUE TRANSFORMATIONS
    # =========================================================================

    def color(
        self,
        color: HSV | str | PaletteRef | None = None,
        *,
        flash: HSV | str | PaletteRef | None = None,
        fade: HSV | str | PaletteRef | None = None,
    ) -> LightPattern:
        """
        Set color properties.

        Args:
            color: Base color for all events (HSV, name string, or palette reference)
            flash: Color during envelope attack phase
            fade: Color during envelope decay/sustain phase

        Examples:
            .color("red")                    # Named color
            .color(palette(0))               # First color from palette
            .color(palette.random)           # Random color from palette
            .color(flash=palette(0), fade=palette(1))  # Flash/fade from palette
        """
        # Pre-resolve literal colors, leave PaletteRef as-is
        base_color = None if isinstance(color, PaletteRef) else resolve_color(color)
        base_ref = color if isinstance(color, PaletteRef) else None
        flash_color = None if isinstance(flash, PaletteRef) else resolve_color(flash)
        flash_ref = flash if isinstance(flash, PaletteRef) else None
        fade_color = None if isinstance(fade, PaletteRef) else resolve_color(fade)
        fade_ref = fade if isinstance(fade, PaletteRef) else None

        def query_color(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            for h in haps:
                new_value = h.value

                # Set base color or palette reference
                if base_color:
                    new_value = new_value.with_color(base_color)
                elif base_ref:
                    new_value = new_value.with_color_ref(base_ref)

                # Apply flash/fade colors/refs to envelope
                if flash_color or fade_color or flash_ref or fade_ref:
                    env = new_value.envelope or Envelope()

                    # Set literal colors
                    if flash_color or fade_color:
                        env = env.with_colors(flash=flash_color, fade=fade_color)

                    # Set palette refs
                    if flash_ref:
                        env = env.with_flash_ref(flash_ref)
                    if fade_ref:
                        env = env.with_fade_ref(fade_ref)

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
                # Chain with existing modulator if present
                if h.value.modulator:
                    chained_mod = h.value.modulator.chain(mod)
                    new_value = h.value.with_modulator(chained_mod)
                else:
                    new_value = h.value.with_modulator(mod)
                result.append(h.with_value(new_value))

            return result

        return LightPattern(query_modulate)

    def wave(
        self,
        wave: str = "sine",
        frequency: float = 1.0,
        min_intensity: float = 0.0,
        max_intensity: float = 1.0,
        direction: int = 1,
        event_relative: bool = False,
    ) -> LightPattern:
        """
        Apply a traveling wave of intensity across lights.

        Each light gets a phase-offset modulation based on its position,
        creating a "loading spinner" or traveling wave effect where a
        bright point moves through the lights.

        Args:
            wave: Waveform type ("sine", "triangle", "saw", "square")
            frequency: Oscillations per bar (1.0 = one full wave travel per bar)
            min_intensity: Minimum intensity (0.0-1.0)
            max_intensity: Maximum intensity (0.0-1.0)
            direction: 1 for forward, -1 for reverse wave direction
            event_relative: If True, wave starts fresh from each event's beginning.
                           Use this with cat() to ensure wave starts at light 0 each time.

        Examples:
            # Smooth sine wave traveling through lights once per bar
            light("all").wave("sine", frequency=1.0)

            # Fast loading spinner (4x per bar)
            light("all").wave("sine", frequency=4.0, min_intensity=0.2)

            # Triangle wave for sharper peak, reverse direction
            light("all").wave("triangle", frequency=2.0, direction=-1)

            # Event-relative wave (starts fresh each event, good for cat())
            light("all ~*3").wave("sine", frequency=4.0, event_relative=True)

        Returns:
            New LightPattern with per-light phase-offset modulation
        """
        wave_type = WaveType(wave.lower())

        def query_wave(span: TimeSpan, ctx: LightContext) -> list[LightHap]:
            haps = self._query(span, ctx)
            result = []

            # Resolve all lights and their positions
            all_lights = list(range(ctx.num_lights))
            n_lights = len(all_lights)

            for hap in haps:
                # Get event start time for event-relative mode
                event_start = float(hap.whole_or_part().start) if event_relative else 0.0

                # Determine which light(s) this hap targets
                if hap.value.light_id is not None:
                    # Single light - use its position for phase
                    light_id = hap.value.light_id
                    light_position = all_lights.index(light_id) if light_id in all_lights else 0
                    # Negative phase = delay = wave travels forward through lights
                    phase = -(light_position / n_lights) * direction

                    mod = Modulator(
                        wave=wave_type,
                        frequency=frequency,
                        min_intensity=min_intensity,
                        max_intensity=max_intensity,
                        phase=phase,
                        reference_time=event_start,
                    )

                    # Chain with existing modulator if present
                    if hap.value.modulator:
                        mod = hap.value.modulator.chain(mod)

                    new_value = hap.value.with_modulator(mod)
                    result.append(hap.with_value(new_value))

                elif hap.value.group:
                    # Group reference - expand to individual lights with phase offsets
                    group_lights = ctx.resolve_group(hap.value.group)
                    for i, light_id in enumerate(group_lights):
                        # Phase based on position within group
                        # Negative phase = delay = wave travels forward through lights
                        phase = -(i / len(group_lights)) * direction

                        mod = Modulator(
                            wave=wave_type,
                            frequency=frequency,
                            min_intensity=min_intensity,
                            max_intensity=max_intensity,
                            phase=phase,
                            reference_time=event_start,
                        )

                        # Chain with existing modulator if present
                        if hap.value.modulator:
                            mod = hap.value.modulator.chain(mod)

                        new_value = LightValue(
                            light_id=light_id,
                            group=None,
                            color=hap.value.color,
                            intensity=hap.value.intensity,
                            envelope=hap.value.envelope,
                            modulator=mod,
                        )
                        result.append(hap.with_value(new_value))
                else:
                    result.append(hap)

            return result

        return LightPattern(query_wave)

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
