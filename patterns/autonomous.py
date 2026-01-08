"""Autonomous patterns - each light behaves independently."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, LightPattern


@pattern("Autonomous", "Each light independently on/off at random beats", tags=["autonomous"])
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


@pattern("Fireflies", "Firefly-like random blinking, warm colors", tags=["autonomous", "ambient"])
def fireflies() -> LightPattern:
    """
    Firefly-like effect with warm colors.

    Each light blinks on for 2-6 beats, then stays off for 2-4 beats.
    Warm color scheme randomized per event.
    """
    return light("all").autonomous(
        min_on=2,
        max_on=6,
        min_off=2,
        max_off=4,
        colors=["yellow", "warm_white", "orange", "amber"],
    )


@pattern("Rainbow Auto", "Autonomous rainbow - random colors, 2-4 beats on/off", tags=["autonomous", "rainbow"])
def rainbow_autonomous() -> LightPattern:
    """
    Autonomous rainbow - each light randomly picks rainbow colors.

    Each light blinks on for 1-4 beats with no off time.
    Colors cycle through the full rainbow spectrum.
    """
    return light("all").autonomous(
        min_on=1,
        max_on=4,
        min_off=0,
        max_off=0,
        colors=[
            "red", "orange", "yellow", "green",
            "cyan", "blue", "purple", "magenta",
        ],
    )
