"""Classic patterns - equivalents of the original engine.py builtins."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, stack, LightPattern, palette


@pattern(
    "Sine Wave",
    "Sine wave with phase spread across lights",
    tags=["classic", "wave"],
    palette="fire",
)
def sine_wave() -> LightPattern:
    """
    Sine wave with phase spread across lights.

    Each light oscillates in a sine wave, phases spread across the group.
    """
    return (
        light("all")
        .seq()
        .modulate(
            wave="sine",
            frequency=0.5,
            min_intensity=0.1,
            max_intensity=1.0,
        )
        .color(palette(0))
    )


@pattern(
    "Slow Wave",
    "Slow ambient wave",
    tags=["classic", "wave", "ambient"],
    palette="warm",
)
def slow_wave() -> LightPattern:
    """Slow ambient wave - gentle pulsing over 4 beats."""
    return (
        light("all")
        .seq()
        .modulate(
            wave="sine",
            frequency=0.25,
            min_intensity=0.1,
            max_intensity=1.0,
        )
        .color(palette(0))
    )


@pattern("Chase", "Sawtooth chase pattern", tags=["classic", "chase"], palette="fire")
def classic_chase() -> LightPattern:
    """Sawtooth chase pattern."""
    return (
        light("all")
        .seq()
        .modulate(
            wave="saw",
            frequency=0.5,
            min_intensity=0.05,
            max_intensity=1.0,
        )
        .color(palette(0))
    )


@pattern(
    "Fast Chase",
    "Fast chase with cool colors",
    tags=["classic", "chase"],
    palette="cool",
)
def fast_chase_classic() -> LightPattern:
    """Fast chase pattern with cool colors."""
    return (
        light("all")
        .seq()
        .modulate(
            wave="saw",
            frequency=1.0,
            min_intensity=0.05,
            max_intensity=1.0,
        )
        .color(palette(0))
    )


@pattern("Pulse", "All lights pulse together on beat", tags=["classic"], palette="fire")
def pulse() -> LightPattern:
    """All lights pulse together - unified pulsing without phase spread."""
    return (
        light("all")
        .modulate(
            wave="sine",
            frequency=4,
            min_intensity=0.3,
            max_intensity=0.8,
        )
        .color(palette(0))
    )


@pattern("Classic Strobe", "Fast strobe on 16th notes", tags=["classic", "strobe"])
def strobe() -> LightPattern:
    """Fast strobe on 16th notes. Keeps white for maximum brightness."""
    return light("all ~").fast(8).color("white")


@pattern(
    "Left Right",
    "Left/right alternating with complementary colors",
    tags=["classic"],
    palette="red_cyan",
)
def left_right() -> LightPattern:
    """Left/right alternating with complementary palette colors."""
    return stack(
        light("left")
        .modulate(wave="sine", frequency=0.5, min_intensity=0.1, max_intensity=1.0)
        .color(palette(0)),
        light("right")
        .modulate(
            wave="sine", frequency=0.5, min_intensity=0.1, max_intensity=1.0, phase=0.5
        )
        .color(palette(1)),
    )
