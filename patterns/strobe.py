"""Strobe patterns - rapid on/off flashing."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, cat, LightPattern, palette


@pattern("Strobe", "16th note white strobe", tags=["strobe"])
def strobe_white() -> LightPattern:
    """Classic strobe - 16th notes on/off."""
    return light("all ~").fast(8).color("white")


@pattern(
    "Strobe (Palette)", "16th note palette strobe", tags=["strobe"], palette="neon"
)
def strobe_palette() -> LightPattern:
    """Palette strobe - 16th notes cycling through palette colors."""
    return light("all ~").fast(16).color(palette.cycle)


@pattern("Strobe Build", "Strobe speeds up over 8 bars", tags=["strobe"])
def strobe_build() -> LightPattern:
    """Strobe that doubles speed every 2 bars (8 bar total build)."""
    return (
        cat(
            light("all ~").fast(2),  # Quarter notes (bars 1-2)
            light("all ~").fast(4),  # 8th notes (bars 3-4)
            light("all ~").fast(8),  # 16th notes (bars 5-6)
            light("all ~").fast(16),  # 32nd notes (bars 7-8)
        )
        .slow(2)
        .color("white")
    )


@pattern(
    "Strobe Build (Palette)",
    "Strobe build with palette colors",
    tags=["strobe"],
    palette="neon",
)
def strobe_build_palette() -> LightPattern:
    """Palette strobe build - doubles speed every 2 bars with palette colors."""
    return (
        cat(
            light("all ~").fast(2),  # Quarter notes (bars 1-2)
            light("all ~").fast(4),  # 8th notes (bars 3-4)
            light("all ~").fast(8),  # 16th notes (bars 5-6)
            light("all ~").fast(16),  # 32nd notes (bars 7-8)
        )
        .slow(2)
        .color(palette.cycle)
    )


@pattern("Strobe Slow", "1/8 note on, 1/8 note off white strobe", tags=["strobe"])
def strobe_slow() -> LightPattern:
    """Slower strobe - 1/8 note on, 1/8 note off."""
    return light("all ~").fast(4).color("white")


@pattern("Strobe Modulated", "Triangle wave strobe via modulation", tags=["strobe"])
def strobe_modulated() -> LightPattern:
    """Strobe using modulation - continuous like fades."""
    return (
        light("all")
        .modulate("triangle", frequency=16, min_intensity=0, max_intensity=1)
        .color("white")
    )


@pattern("Strobe Mod Slow", "Slow triangle wave (2 per bar)", tags=["strobe"])
def strobe_mod_slow() -> LightPattern:
    """Very slow modulation to test if rate matters."""
    return (
        light("all")
        .modulate("triangle", frequency=2, min_intensity=0, max_intensity=1)
        .color("white")
    )


@pattern("Strobe Modulated Sine", "Sine wave strobe via modulation", tags=["strobe"])
def strobe_modulated_sine() -> LightPattern:
    """Sine wave strobe - even smoother transitions."""
    return (
        light("all")
        .modulate("saw", frequency=16, min_intensity=0.1, max_intensity=1)
        .color("white")
    )


@pattern("Strobe Modulated Square", "Square wave via modulation", tags=["strobe"])
def strobe_modulated_square() -> LightPattern:
    """Square wave strobe - hard on/off but via modulation path."""
    return light("all").fast(4).envelope(attack=0.01, decay=0.5, sustain=0.0)
