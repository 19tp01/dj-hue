"""
Pattern engine for DJ-Hue.

This module provides the pattern engine with:
- Light grouping (zones like left/right, front/back)
- Declarative pattern definitions
- Color palettes for flexible color schemes
- Hot-reload capability

The pattern engine extends the core primitives from lights.effects
(Phaser, BeatClock, RGB) with higher-level abstractions.
"""

from .common.groups import LightGroup, LightSetup, ZoneType
from .classic.pattern_def import Pattern, PatternDef, GroupEffect, ColorPalette, HSV
from .engine import PatternEngine, QuickAction
from .classic.loader import PatternLoader

# Re-export Phaser for convenience in pattern files
from ..lights.effects import Phaser

__all__ = [
    # Groups
    "LightGroup",
    "LightSetup",
    "ZoneType",
    # Patterns
    "Pattern",
    "PatternDef",  # Backwards compatibility
    "GroupEffect",
    "ColorPalette",
    "HSV",
    "Phaser",
    # Engine
    "PatternEngine",
    "QuickAction",
    # Loader
    "PatternLoader",
]
