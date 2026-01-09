"""Ambient patterns - slow, gentle effects."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, cat, LightPattern, palette


@pattern("Gentle", "Slow ambient pulse", tags=["ambient"], palette="warm")
def gentle_pulse() -> LightPattern:
    """Slow ambient pulse, all lights together."""
    return (
        light("all")
        .envelope(attack=0.5, fade=0.5, sustain=0.3)
        .slow(2)
        .color(palette(0))
    )


@pattern("Color Wash", "Slow color cycling across lights", tags=["ambient"], palette="warm")
def color_wash() -> LightPattern:
    """Slow wave across lights cycling through palette colors (8 bar cycle)."""
    return (
        cat(
            light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4),
            light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4),
            light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4),
            light("all").seq().envelope(attack=0.3, fade=0.5, sustain=0.4),
        )
        .color(palette.cycle)
        .slow(2)
    )
