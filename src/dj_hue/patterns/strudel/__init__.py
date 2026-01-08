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
from .modulator import Modulator, WaveType
from .constructors import light, stack, cat, all_lights, sequence, zone, ceiling, perimeter
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
from .layered import LayeredPattern, ZoneLayer
from .presets_v2 import get_spatial_presets
from .combiner import (
    combine_zone_layers,
    create_spatial_delay_pattern,
    create_echo_pattern,
    create_alternating_zones_pattern,
)

__all__ = [
    # Core types
    "TimeSpan",
    "LightHap",
    "LightValue",
    "LightContext",
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
    "zone",
    "ceiling",
    "perimeter",

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
    "get_spatial_presets",

    # Layered patterns
    "LayeredPattern",
    "ZoneLayer",
    "combine_zone_layers",
    "create_spatial_delay_pattern",
    "create_echo_pattern",
    "create_alternating_zones_pattern",
]
