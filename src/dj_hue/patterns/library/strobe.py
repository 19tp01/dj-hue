"""Strobe patterns - rapid on/off flashing."""

from ..decorator import pattern
from ..strudel import light, cat, LightPattern


@pattern("s_strobe", "16th note white strobe", tags=["strobe"])
def strobe_white() -> LightPattern:
    """Classic strobe - 16th notes on/off."""
    return light("all ~").fast(16).color("white")


@pattern("s_strobe_build", "Strobe speeds up over 8 bars", tags=["strobe"])
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
