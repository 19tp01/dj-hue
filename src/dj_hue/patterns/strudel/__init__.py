"""
Strudel-inspired pattern language for dj-hue.

A composable pattern system where complex lighting effects emerge
from chaining simple primitives.

Example:
    from dj_hue.patterns.strudel import light, stack, cat

    # Stagger flash: random sequence, flash white, fade to red
    stagger_flash = (
        light("all")
        .seq()
        .shuffle()
        .envelope(attack=0.05, fade=4.0, sustain=0.5)
        .color(flash="white", fade="red")
    )

    # Simple pulse
    pulse = light("all all all all").envelope(attack=0.1, decay=0.15).color("red")

    # Strobe build
    strobe_build = cat(
        light("all ~").fast(2),
        light("all ~").fast(4),
        light("all ~").fast(8),
        light("all ~").fast(16),
    ).slow(2)

    # Zone targeting
    spatial = stack(
        strobe().zone("ceiling"),
        chase().zone("perimeter"),
    )
"""

# Core types
from .core.types import TimeSpan, LightHap, LightValue, LightContext, HSV
from .core.pattern import LightPattern
from .core.envelope import Envelope

# Modulator
from .modulator import Modulator, WaveType

# DSL constructors
from .dsl.constructors import light, stack, cat, all_lights, sequence, ceiling, perimeter

# Scheduler
from .scheduler import PatternScheduler, StrudelPatternWrapper

# Colors
from .color import (
    color_from_name,
    resolve_color,
    hex_to_hsv,
    hue_rotate,
    dim,
    saturate,
    NAMED_COLORS,
)

# Palette system
from .palette import palette, Palette, PaletteRef
from .palettes import get_palette, register_palette, list_palettes, PALETTES

__all__ = [
    # Core types
    "TimeSpan",
    "LightHap",
    "LightValue",
    "LightContext",
    "HSV",
    "LightPattern",
    "Envelope",
    "Modulator",
    "WaveType",
    # Constructors
    "light",
    "stack",
    "cat",
    "all_lights",
    "sequence",
    "ceiling",
    "perimeter",
    # Scheduler
    "PatternScheduler",
    "StrudelPatternWrapper",
    # Colors
    "color_from_name",
    "resolve_color",
    "hex_to_hsv",
    "hue_rotate",
    "dim",
    "saturate",
    "NAMED_COLORS",
    # Palette system
    "palette",
    "Palette",
    "PaletteRef",
    "get_palette",
    "register_palette",
    "list_palettes",
    "PALETTES",
]
