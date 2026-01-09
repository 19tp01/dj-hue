"""Strobe patterns - rapid on/off flashing."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, cat, LightPattern, palette


@pattern("Strobe", "16th note white strobe", tags=["strobe"])
def strobe_white() -> LightPattern:
    """Classic strobe - 16th notes on/off."""
    return light("all ~").fast(16).color("white")


@pattern("Strobe (Palette)", "16th note palette strobe", tags=["strobe"], palette="neon")
def strobe_palette() -> LightPattern:
    """Palette strobe - 16th notes cycling through palette colors."""
    return light("all ~").fast(16).color(palette.cycle)


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


@pattern("Strobe Build (Palette)", "Strobe build with palette colors", tags=["strobe"], palette="neon")
def strobe_build_palette() -> LightPattern:
    """Palette strobe build - doubles speed every 2 bars with palette colors."""
    return (
        cat(
            light("all ~").fast(2),   # Quarter notes (bars 1-2)
            light("all ~").fast(4),   # 8th notes (bars 3-4)
            light("all ~").fast(8),   # 16th notes (bars 5-6)
            light("all ~").fast(16),  # 32nd notes (bars 7-8)
        )
        .slow(2)
        .color(palette.cycle)
    )


@pattern("Strobe Slow", "1/8 note on, 1/8 note off white strobe", tags=["strobe"])
def strobe_slow() -> LightPattern:
    """Slower strobe - 1/8 note on, 1/8 note off."""
    return light("all ~").fast(4).color("white")


@pattern("Strobe Slow (Palette)", "1/8 note palette strobe", tags=["strobe"], palette="neon")
def strobe_slow_palette() -> LightPattern:
    """Slower palette strobe - 1/8 note on, 1/8 note off with palette colors."""
    return light("all ~").fast(4).color(palette.cycle)
