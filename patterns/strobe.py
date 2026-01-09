"""Strobe patterns - rapid on/off flashing."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, cat, LightPattern


@pattern("Strobe", "16th note white strobe", tags=["strobe"])
def strobe_white() -> LightPattern:
    """Classic strobe - 16th notes on/off."""
    return light("all ~").fast(16).color("white")


@pattern("Strobe Build", "Strobe speeds up over 8 bars", tags=["strobe"])
def strobe_build() -> LightPattern:
    """Strobe that doubles speed every 2 bars (8 bar total build)."""
    return (
        cat(
            light("all ~").fast(2),   # Quarter notes (bars 1-2)
            light("all ~").fast(4),   # 8th notes (bars 3-4)
            light("all ~").fast(8),   # 16th notes (bars 5-6)
            light("all ~").fast(16),  # 32nd notes (bars 7-8)
        )
        .slow(2)
        .color("white")
    )


@pattern("Strobe Slow", "1/8 note on, 1/8 note off white strobe", tags=["strobe"])
def strobe_slow() -> LightPattern:
    """Slower strobe - 1/8 note on, 1/8 note off."""
    return light("all ~").fast(4).color("white")
