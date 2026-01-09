"""Chase patterns - lights sequence around."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, stack, cat, LightPattern, palette


@pattern("Chase Smooth", "Lights chase smoothly around", tags=["chase"], palette="cool")
def smooth_chase() -> LightPattern:
    """
    Lights sequence around once per bar with smooth transitions.

    Automatically runs per-group (strip sequences separately from lamps).
    """
    return (
        light("all")
        .seq()
        .envelope(attack=0.1, fade=0.3, sustain=0.2)
        .color(palette(0))
        .early(0.02)
    )


@pattern("Chase Fast", "Quick chase, 4x per bar", tags=["chase"], palette="neon")
def fast_chase() -> LightPattern:
    """Fast chase - 4 cycles per bar."""
    return (
        light("all")
        .seq()
        .fast(4)
        .envelope(attack=0.02, fade=0.1)
        .color(palette(0))
    )


@pattern("Chase Bounce", "Chase bounces back and forth", tags=["chase"], palette="cool")
def bounce_chase() -> LightPattern:
    """
    Chase that bounces back and forth.

    Forward chase then reverse chase, twice per bar.
    """
    forward = stack(
        light("0 1 2 3").envelope(attack=0.05, fade=0.2).color(palette(0)),
        light("4 5").envelope(attack=0.05, fade=0.2).color(palette(0)),
    )
    backward = stack(
        light("3 2 1 0").envelope(attack=0.05, fade=0.2).color(palette(0)),
        light("5 4").envelope(attack=0.05, fade=0.2).color(palette(0)),
    )
    return cat(forward, backward).fast(2)
