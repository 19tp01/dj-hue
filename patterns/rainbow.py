"""Rainbow patterns - color cycling effects."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, cat, LightPattern, palette


@pattern("Rainbow Cycle", "Slow rainbow color cycle", tags=["rainbow", "ambient"], palette="rainbow")
def rainbow_cycle() -> LightPattern:
    """
    Slow rainbow cycle through all colors.

    8-bar cycle through the full spectrum using palette colors.
    """
    return (
        cat(*[light("all") for _ in range(8)])
        .color(palette.cycle)
        .slow(2)
    )


@pattern("Rainbow Wave", "Rainbow wave across lights", tags=["rainbow"], palette="rainbow")
def rainbow_wave() -> LightPattern:
    """
    Rainbow colors wave across lights with offset.

    Uses palette.cycle to cycle through rainbow colors with modulation.
    """
    return (
        cat(*[light("all").seq() for _ in range(8)])
        .color(palette.cycle)
        .fast(4)  # 2 colors per bar
        .modulate(
            wave="sine",
            frequency=0.25,
            min_intensity=0.5,
            max_intensity=1.0,
        )
    )
