"""Classic patterns - equivalents of the original engine.py builtins."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, stack, LightPattern


@pattern(
    "Sine Wave", "Sine wave with phase spread across lights", tags=["classic", "wave"]
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
        .color("red")
    )


@pattern("Slow Wave", "Slow ambient wave", tags=["classic", "wave", "ambient"])
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
        .color("orange")
    )


@pattern("Chase", "Sawtooth chase pattern", tags=["classic", "chase"])
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
        .color("red")
    )


@pattern("Fast Chase", "Fast chase with cool colors", tags=["classic", "chase"])
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
        .color("cyan")
    )


@pattern("Pulse", "All lights pulse together on beat", tags=["classic"])
def pulse() -> LightPattern:
    """All lights pulse together - unified pulsing without phase spread."""
    return (
        light("all")
        .modulate(
            wave="sine",
            frequency=1.0,
            min_intensity=0.3,
            max_intensity=0.8,
        )
        .color("red")
    )


@pattern("Classic Strobe", "Fast strobe on 16th notes", tags=["classic", "strobe"])
def strobe() -> LightPattern:
    """Fast strobe on 16th notes."""
    return light("all ~").fast(8).color("white")


@pattern("Left Right", "Left/right alternating with red/blue", tags=["classic"])
def left_right() -> LightPattern:
    """Left/right alternating with red/blue."""
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
