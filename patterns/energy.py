"""Energy patterns - dynamic, high-energy effects."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, stack, LightPattern


@pattern("Alternate", "Left/right alternating", tags=["energy"])
def alternating() -> LightPattern:
    """Left and right groups alternate each half bar."""
    return stack(
        light("left ~").color("red"),
        light("~ right").color("blue"),
    )


@pattern("Random Pop", "Random lights pop on each beat", tags=["energy"])
def random_pop() -> LightPattern:
    """Random lights pop on each beat with quick fade."""
    return (
        light("all all all all")
        .seq()
        .shuffle()
        .envelope(attack=0.01, fade=0.2)
        .color(flash="white", fade="yellow")
    )
