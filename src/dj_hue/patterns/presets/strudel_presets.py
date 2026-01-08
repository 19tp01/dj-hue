"""
Pre-built Strudel patterns for common DJ lighting effects.

These patterns can be registered with PatternEngine using register_strudel_pattern().
"""

from ..strudel.dsl.constructors import light, stack, cat
from ..strudel.core.pattern import LightPattern


def get_strudel_presets() -> dict[str, tuple[LightPattern, str]]:
    """
    Get all preset Strudel patterns.

    Returns:
        Dict mapping pattern name to (LightPattern, description) tuples.
    """
    return {
        # === FLASH PATTERNS ===
        "s_stagger": (
            stagger_flash(),
            "Random sequential white flash, fades to red",
        ),
        "s_beat_flash": (
            beat_flash(),
            "All lights flash on each beat",
        ),
        "s_downbeat": (
            downbeat_flash(),
            "Flash on beat 1 only",
        ),
        # === CHASE PATTERNS ===
        "s_chase_smooth": (
            smooth_chase(),
            "Lights chase smoothly around",
        ),
        "s_chase_fast": (
            fast_chase(),
            "Quick chase, 4x per bar",
        ),
        "s_chase_bounce": (
            bounce_chase(),
            "Chase bounces back and forth",
        ),
        # === STROBE PATTERNS ===
        "s_strobe": (
            strobe_white(),
            "16th note white strobe",
        ),
        "s_strobe_build": (
            strobe_build(),
            "Strobe speeds up over 8 bars",
        ),
        # === AMBIENT PATTERNS ===
        "s_gentle": (
            gentle_pulse(),
            "Slow ambient pulse",
        ),
        "s_color_wash": (
            color_wash(),
            "Slow color cycling across lights",
        ),
        # === ENERGY PATTERNS ===
        "s_alternate": (
            alternating(),
            "Left/right alternating",
        ),
        "s_random_pop": (
            random_pop(),
            "Random lights pop on each beat",
        ),
        # === SIGNATURE PATTERNS ===
        "s_green_cascade": (
            green_cascade(),
            "Neon green with sequential white flash at bar start",
        ),
        "s_blue_fade_strobe": (
            blue_fade_strobe(),
            "2 beats bright blue fade, 2 beats blue strobe",
        ),
        # === RAINBOW PATTERNS ===
        "s_rainbow_chase": (
            rainbow_chase(),
            "Rainbow colors chase on half notes",
        ),
        "s_rainbow_breathe": (
            rainbow_breathe(),
            "Rainbow colors with sine wave breathing 80-100%",
        ),
        # === AUTONOMOUS PATTERNS ===
        "s_autonomous": (
            autonomous_lights(),
            "Each light independently on/off at random beats",
        ),
        "s_fireflies": (
            fireflies(),
            "Firefly-like random blinking, warm colors",
        ),
        "s_rainbow_auto": (
            rainbow_autonomous(),
            "Autonomous rainbow - random colors, 2-4 beats on/off",
        ),
        # === CLASSIC PATTERN EQUIVALENTS (replacing engine.py builtins) ===
        "sine_wave": (
            sine_wave(),
            "Sine wave with phase spread across lights",
        ),
        "slow_wave": (
            slow_wave(),
            "Slow ambient wave",
        ),
        "chase": (
            classic_chase(),
            "Sawtooth chase pattern",
        ),
        "fast_chase": (
            fast_chase_classic(),
            "Fast chase with cool colors",
        ),
        "pulse": (
            pulse(),
            "All lights pulse together on beat",
        ),
        "strobe": (
            strobe(),
            "Fast strobe on 16th notes",
        ),
        "left_right": (
            left_right(),
            "Left/right alternating with red/blue",
        ),
    }


# =============================================================================
# FLASH PATTERNS
# =============================================================================


def stagger_flash() -> LightPattern:
    """
    Random sequential white flash, each light fades to red.

    Original request: "at the start of each bar, lights in a random sequence
    flash white successively in 16th notes at max brightness then dark,
    then fades up to 50% of a single color until the next sequenced flash"
    """
    return (
        light("all")
        .seq(per_group=False)  # Sequence ALL lights together
        .shuffle()
        .envelope(attack=0.05, fade=1.0, sustain=0.5)
        .color(flash="white", fade="red")
    )


def beat_flash() -> LightPattern:
    """All lights flash white on each beat (4 times per bar)."""
    return (
        light("all all all all")
        .envelope(attack=0.02, fade=0.2)
        .color(flash="white", fade="cyan")
    )


def downbeat_flash() -> LightPattern:
    """Single flash on beat 1, fades for rest of bar."""
    # fade=1.0 means fade over 1 full cycle (bar), sustain=0 means fade to black
    return (
        light("all ~*3")
        .envelope(attack=0.02, fade=1.0, sustain=0.0)
        .color(flash="white", fade="orange")
    )


# =============================================================================
# CHASE PATTERNS
# =============================================================================


def smooth_chase() -> LightPattern:
    """
    Lights sequence around once per bar with smooth transitions.

    Automatically runs per-group (strip sequences separately from lamps).
    """
    return (
        light("all")
        .seq()
        .envelope(attack=0.1, fade=0.3, sustain=0.2)
        .color("cyan")
        .early(0.02)  # Start slightly early so first light is visible at bar start
    )


def fast_chase() -> LightPattern:
    """
    Fast chase - 4 cycles per bar.

    Automatically runs per-group (strip sequences separately from lamps).
    """
    return light("all").seq().fast(4).envelope(attack=0.02, fade=0.1).color("magenta")


def bounce_chase() -> LightPattern:
    """
    Chase that bounces back and forth.

    Forward chase then reverse chase, twice per bar.
    Uses explicit light indices for smooth bounce effect.
    """
    # Forward: 0 -> 1 -> 2 -> 3 (strip) and 4 -> 5 (lamps)
    # Backward: 3 -> 2 -> 1 -> 0 (strip) and 5 -> 4 (lamps)
    forward = stack(
        light("0 1 2 3").envelope(attack=0.05, fade=0.2).color("blue"),
        light("4 5").envelope(attack=0.05, fade=0.2).color("blue"),
    )
    backward = stack(
        light("3 2 1 0").envelope(attack=0.05, fade=0.2).color("blue"),
        light("5 4").envelope(attack=0.05, fade=0.2).color("blue"),
    )
    return cat(forward, backward).fast(2)


# =============================================================================
# STROBE PATTERNS
# =============================================================================


def strobe_white() -> LightPattern:
    """Classic strobe - 16th notes on/off."""
    return (
        light("all ~").fast(16).color("white")
    )  # 32 events per bar = 16th note strobe


def strobe_build() -> LightPattern:
    """Strobe that doubles speed every 2 bars (8 bar total build)."""
    return (
        cat(
            light("all ~").fast(2),  # Quarter notes (bars 1-2)
            light("all ~").fast(4),  # 8th notes (bars 3-4)
            light("all ~").fast(8),  # 16th notes (bars 5-6)
            light("all ~").fast(16),  # 32nd notes (bars 7-8)
        )
        .slow(2)
        .color("white")
    )  # Each pattern gets 2 bars


# =============================================================================
# AMBIENT PATTERNS
# =============================================================================


def gentle_pulse() -> LightPattern:
    """Slow ambient pulse, all lights together."""
    return (
        light("all")
        .envelope(attack=0.5, fade=0.5, sustain=0.3)
        .slow(2)  # 2 bars per pulse
        .color("orange")
    )


def color_wash() -> LightPattern:
    """Slow wave across lights cycling through warm colors (8 bar cycle)."""
    return cat(
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("red"),
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("orange"),
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("yellow"),
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("orange"),
    ).slow(
        2
    )  # Each color gets 2 bars = 8 bar total cycle


# =============================================================================
# ENERGY PATTERNS
# =============================================================================


def alternating() -> LightPattern:
    """Left and right groups alternate each half bar."""
    return stack(
        light("left ~").color("red"),
        light("~ right").color("blue"),
    )


def random_pop() -> LightPattern:
    """Random lights pop on each beat with quick fade."""
    return (
        light("all all all all")
        .seq()
        .shuffle()
        .envelope(attack=0.01, fade=0.2)
        .color(flash="white", fade="yellow")
    )


# =============================================================================
# SIGNATURE PATTERNS
# =============================================================================


def green_cascade() -> LightPattern:
    """
    Neon green with alternating even/odd pulse and sequential flash at bar start.

    Base: Even lights pulse on quarter notes 1,3
          Odd lights pulse on quarter notes 2,4
    Flash: Sequential white flash through ALL lights on 16th notes

    Works with any number of lights - uses dynamic groups.
    The flash layer overrides the base layer.
    """
    return stack(
        # Base layer: Even lights on quarter notes 1 and 3
        light("even ~ even ~")
        .envelope(attack=0.02, fade=0.2, sustain=0.8)
        .color("lime"),
        # Base layer: Odd lights on quarter notes 2 and 4
        light("~ odd ~ odd").envelope(attack=0.02, fade=0.2, sustain=0.8).color("lime"),
        # Flash layer: sequential white flash through ALL lights (not per-group)
        light("all")
        .seq(slots=16, per_group=False)  # Flash ALL lights together
        .envelope(attack=0.01, fade=0.12)
        .color(flash="white", fade="lime"),
    )


def blue_fade_strobe() -> LightPattern:
    """
    2 beats bright blue fade to 50%, then 2 beats blue strobe.
    All within one bar.

    First half of bar (beats 1-2): Bright blue flash, fades to 50% over full 2 beats
    Second half of bar (beats 3-4): Blue strobe at 16th note speed
    """
    return cat(
        # 2 beats: bright blue fading to 50% over the full duration
        light("all").envelope(attack=0.02, fade=0.95, sustain=0.2).color("blue"),
        # 2 beats: blue strobe (16th notes = rapid on/off)
        light("all ~")
        .fast(4)  # 8 events in this section = 16th notes within 2 beats
        .color("blue"),
    ).fast(
        2
    )  # Compress 2 cycles into 1 bar (each section = 2 beats)


def rainbow_chase() -> LightPattern:
    """
    Rainbow colors chase through lights on half notes.

    Each half note (2 per bar), lights sequence through with a new color.
    Colors cycle: red -> orange -> yellow -> green -> cyan -> blue -> purple -> magenta
    Full rainbow cycle takes 4 bars.
    """
    # 8 colors, each gets half a bar, so full cycle = 4 bars
    return cat(
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("red"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("orange"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("yellow"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("green"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("cyan"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("blue"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("purple"),
        light("all")
        .seq()
        .envelope(attack=0.02, fade=0.4, sustain=0.0)
        .color("magenta"),
    ).fast(
        2
    )  # 2x speed = half note per color (2 colors per bar)


def rainbow_breathe() -> LightPattern:
    """
    Rainbow colors fading smoothly with brightness sine wave.

    Colors cycle through the full spectrum (8 colors per bar).
    Brightness oscillates from 80% to 100% every 4 bars using a triangle wave
    (always changing, no lingering at min/max).
    """
    return (
        cat(
            light("all").color("red"),
            light("all").color("orange"),
            light("all").color("yellow"),
            light("all").color("green"),
            light("all").color("cyan"),
            light("all").color("blue"),
            light("all").color("purple"),
            light("all").color("magenta"),
        )
        .fast(8)  # 8 colors per bar
        .modulate(
            wave="triangle",  # Triangle wave = always changing, no lingering
            frequency=0.25,  # One full oscillation per 4 bars
            min_intensity=0.8,
            max_intensity=1.0,
            phase=0.25,  # Start at max (sine peaks at phase 0.25)
        )
    )


# =============================================================================
# AUTONOMOUS PATTERNS
# =============================================================================


def autonomous_lights() -> LightPattern:
    """
    Each light behaves independently with random on/off timing.

    Lights turn on for 1-4 beats, then off for 1-2 beats.
    No fading - instant on/off at beat boundaries.
    """
    return (
        light("all")
        .autonomous(
            min_on=1,
            max_on=4,
            min_off=1,
            max_off=2,
        )
        .color("white")
    )


def fireflies() -> LightPattern:
    """
    Firefly-like effect with warm colors.

    Each light blinks on for 2-6 beats, then stays off for 2-4 beats.
    Warm color scheme: yellow, gold, orange, amber - randomized per event.
    """
    return light("all").autonomous(
        min_on=2,
        max_on=6,
        min_off=2,
        max_off=4,
        colors=["yellow", "warm_white", "orange", "amber"],
    )


def rainbow_autonomous() -> LightPattern:
    """
    Autonomous rainbow - each light randomly picks rainbow colors.

    Each light blinks on for 1-2 beats, off for 1-2 beats.
    Colors: red, orange, yellow, green, cyan, blue, purple, magenta.
    """
    return light("all").autonomous(
        min_on=1,
        max_on=4,
        min_off=0,
        max_off=0,
        colors=[
            "red",
            "orange",
            "yellow",
            "green",
            "cyan",
            "blue",
            "purple",
            "magenta",
        ],
    )


# =============================================================================
# CLASSIC PATTERN EQUIVALENTS
# =============================================================================
# These replace the patterns from get_builtin_patterns() in engine.py
# They use .modulate() for continuous LFO-style animation


def sine_wave() -> LightPattern:
    """
    Sine wave with phase spread across lights.

    Replaces Pattern.create_simple with waveform="sine", phase_spread=True.
    Each light oscillates in a sine wave, phases spread across the group.
    """
    return (
        light("all")
        .seq()  # Sequence creates phase spread
        .modulate(
            wave="sine",
            frequency=0.5,  # 2 beats per cycle (matches beats_per_cycle=2.0)
            min_intensity=0.1,
            max_intensity=1.0,
        )
        .color("red")
    )


def slow_wave() -> LightPattern:
    """
    Slow ambient wave - gentle pulsing.

    Replaces Pattern.create_simple with beats_per_cycle=4.0.
    """
    return (
        light("all")
        .seq()
        .modulate(
            wave="sine",
            frequency=0.25,  # 4 beats per cycle
            min_intensity=0.1,
            max_intensity=1.0,
        )
        .color("orange")
    )


def classic_chase() -> LightPattern:
    """
    Sawtooth chase pattern.

    Replaces Pattern.create_chase with waveform="sawtooth".
    """
    return (
        light("all")
        .seq()
        .modulate(
            wave="saw",
            frequency=0.5,  # 2 beats per cycle
            min_intensity=0.05,
            max_intensity=1.0,
        )
        .color("red")
    )


def fast_chase_classic() -> LightPattern:
    """
    Fast chase pattern with cool colors.

    Replaces Pattern.create_chase with beats_per_cycle=1.0.
    """
    return (
        light("all")
        .seq()
        .modulate(
            wave="saw",
            frequency=1.0,  # 1 beat per cycle = faster
            min_intensity=0.05,
            max_intensity=1.0,
        )
        .color("cyan")
    )


def pulse() -> LightPattern:
    """
    All lights pulse together on beat.

    Replaces Pattern.create_pulse - unified pulsing without phase spread.
    """
    return (
        light("all")
        .modulate(
            wave="sine",
            frequency=1.0,  # 1 beat per cycle
            min_intensity=0.1,
            max_intensity=1.0,
        )
        .color("red")
    )


def strobe() -> LightPattern:
    """
    Fast strobe on 16th notes.

    Replaces Pattern.create_strobe with square wave.
    """
    return light("all ~").fast(8).color("white")  # 16 events per bar = 16th notes


def left_right() -> LightPattern:
    """
    Left/right alternating with red/blue.

    Replaces Pattern.create_left_right.
    """
    return stack(
        light("left")
        .modulate(wave="sine", frequency=0.5, min_intensity=0.1, max_intensity=1.0)
        .color("red"),
        light("right")
        .modulate(
            wave="sine", frequency=0.5, min_intensity=0.1, max_intensity=1.0, phase=0.5
        )
        .color("blue"),
    )
