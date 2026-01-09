"""Smooth rainbow color transitions with pulsing intensity."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, LightPattern, palette


@pattern(
    "Rainbow Fade",
    "Smooth rainbow blend with sawtooth pulse",
    tags=["rainbow", "ambient"],
    palette="rainbow",
)
def rainbow_fade() -> LightPattern:
    """All lights smoothly transition through rainbow colors every bar.

    Sawtooth intensity from 100% to 50% every two beats creates a
    gentle pulsing effect while colors continuously blend.
    """
    return (
        light("all")
        .color(palette.random_blend(2, 2))  # Continuous blend through palette every bar
        .modulate(
            "saw", frequency=1.0, min_intensity=1.0, max_intensity=0.8
        )  # 100→50% every 2 beats
    )
