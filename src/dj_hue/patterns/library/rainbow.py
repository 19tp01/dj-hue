"""Rainbow patterns - color cycling effects."""

from ..decorator import pattern
from ..strudel import light, cat, LightPattern


@pattern("rainbow_cycle", "Slow rainbow color cycle", tags=["rainbow", "ambient"])
def rainbow_cycle() -> LightPattern:
    """
    Slow rainbow cycle through all colors.

    8-bar cycle through the full spectrum.
    """
    return cat(
        light("all").color("red"),
        light("all").color("orange"),
        light("all").color("yellow"),
        light("all").color("green"),
        light("all").color("cyan"),
        light("all").color("blue"),
        light("all").color("purple"),
        light("all").color("magenta"),
    ).slow(2)


@pattern("rainbow_wave", "Rainbow wave across lights", tags=["rainbow"])
def rainbow_wave() -> LightPattern:
    """
    Rainbow colors wave across lights with offset.

    Uses cat() to cycle through rainbow colors with modulation.
    """
    return (
        cat(
            light("all").seq().color("red"),
            light("all").seq().color("orange"),
            light("all").seq().color("yellow"),
            light("all").seq().color("green"),
            light("all").seq().color("cyan"),
            light("all").seq().color("blue"),
            light("all").seq().color("purple"),
            light("all").seq().color("magenta"),
        )
        .fast(4)  # 2 colors per bar
        .modulate(
            wave="sine",
            frequency=0.25,
            min_intensity=0.5,
            max_intensity=1.0,
        )
    )
