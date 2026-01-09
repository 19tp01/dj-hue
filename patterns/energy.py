"""Energy patterns - dynamic, high-energy effects."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, stack, LightPattern, palette


@pattern("Alternate", "Left/right alternating", tags=["energy"], palette="red_cyan")
def alternating() -> LightPattern:
    """Left and right groups alternate each half bar."""
    return stack(
        light("left ~").color(palette(0)),
        light("~ right").color(palette(1)),
    )


@pattern(
    "Random Pop", "Random lights pop on each beat", tags=["energy"], palette="golden"
)
def random_pop() -> LightPattern:
    """1-2 random lights pop on each beat with quick fade."""
    return (
        light("all all all all")
        .pick(0.5)
        .envelope(attack=0.01, fade=0.2)
        .color(flash="white", fade=palette(0))
    )
