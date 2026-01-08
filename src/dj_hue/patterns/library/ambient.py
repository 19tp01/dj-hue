"""Ambient patterns - slow, gentle effects."""

from ..decorator import pattern
from ..strudel import light, cat, LightPattern


@pattern("s_gentle", "Slow ambient pulse", tags=["ambient"])
def gentle_pulse() -> LightPattern:
    """Slow ambient pulse, all lights together."""
    return (
        light("all")
        .envelope(attack=0.5, fade=0.5, sustain=0.3)
        .slow(2)
        .color("orange")
    )


@pattern("s_color_wash", "Slow color cycling across lights", tags=["ambient"])
def color_wash() -> LightPattern:
    """Slow wave across lights cycling through warm colors (8 bar cycle)."""
    return cat(
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("red"),
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("orange"),
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("yellow"),
        light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4).color("orange"),
    ).slow(2)
