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
"""

from .core import TimeSpan, LightHap, LightValue, LightContext
from .pattern import LightPattern
from .envelope import Envelope
from .constructors import light, stack, cat, all_lights, sequence
from .scheduler import PatternScheduler, StrudelPatternWrapper
from .colors import (
    color_from_name,
    resolve_color,
    hue_rotate,
    dim,
    saturate,
    NAMED_COLORS,
)
from .presets import get_strudel_presets

__all__ = [
    # Core types
    "TimeSpan",
    "LightHap",
    "LightValue",
    "LightContext",
    "LightPattern",
    "Envelope",

    # Constructors
    "light",
    "stack",
    "cat",
    "all_lights",
    "sequence",

    # Scheduler
    "PatternScheduler",
    "StrudelPatternWrapper",

    # Colors
    "color_from_name",
    "resolve_color",
    "hue_rotate",
    "dim",
    "saturate",
    "NAMED_COLORS",

    # Presets
    "get_strudel_presets",
]
