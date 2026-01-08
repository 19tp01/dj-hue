"""
Pre-built Strudel patterns for common DJ lighting effects.

These patterns can be registered with PatternEngine using register_strudel_pattern().
"""

from .constructors import light, stack, cat
from .pattern import LightPattern


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
        # === BRIGHTNESS AUTOMATION PATTERNS ===
        "s_breathe": (
            breathe(),
            "Smooth sine wave breathing, 2 beats per cycle",
        ),
        "s_ramp_up": (
            ramp_up(),
            "Linear brightness ramp, resets each beat",
        ),
        "s_pulse_wave": (
            pulse_wave(),
            "Sharp pulse decay on each beat",
        ),
        "s_triangle_chase": (
            triangle_chase(),
            "Chase with triangle wave brightness",
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
    """Single flash on beat 1, rest of bar is ambient glow."""
    return stack(
        # Ambient base layer - continuous dim glow
        light("all").envelope(attack=0.5, fade=0.5, sustain=0.3).color("orange").intensity(0.3),
        # Flash overlay on beat 1
        light("all ~*15").envelope(attack=0.02, fade=0.5).color(flash="white", fade="orange"),
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
    return light("all ~").fast(16).color("white")  # 32 events per bar = 16th note strobe


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
    ).slow(2)  # Each color gets 2 bars = 8 bar total cycle


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


# =============================================================================
# BRIGHTNESS AUTOMATION PATTERNS
# =============================================================================


def breathe() -> LightPattern:
    """
    Smooth sine wave breathing effect.

    Uses Phaser to modulate brightness with a sine wave.
    2 beats per full cycle (0->1->0).
    """
    return (
        light("all")
        .brightness(waveform="sine", beats=2, min_val=0.1, max_val=1.0)
        .color("cyan")
    )


def ramp_up() -> LightPattern:
    """
    Linear brightness ramp that resets each beat.

    Sawtooth wave: 0->1 over 1 beat, instant reset.
    Good for build-ups or tension.
    """
    return (
        light("all")
        .brightness(waveform="sawtooth", beats=1, min_val=0.0, max_val=1.0)
        .color("red")
    )


def pulse_wave() -> LightPattern:
    """
    Sharp exponential decay pulse on each beat.

    Smooth pulse waveform: instant peak, exponential decay.
    """
    return (
        light("all")
        .brightness(waveform="smooth_pulse", beats=1, min_val=0.0, max_val=1.0)
        .color("white")
    )


def triangle_chase() -> LightPattern:
    """
    Chase pattern with triangle wave brightness.

    Combines sequential light movement with smooth brightness oscillation.
    """
    return (
        light("all")
        .seq()
        .brightness(waveform="triangle", beats=2, min_val=0.2, max_val=1.0)
        .color("magenta")
    )
