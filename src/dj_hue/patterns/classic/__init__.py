"""
Classic pattern system for DJ-Hue.

This is the original declarative, Phaser-based pattern system.
Patterns are defined as dataclasses that reference light groups by name.
"""

from .pattern_def import Pattern, PatternDef, GroupEffect, ColorPalette, HSV
from .loader import PatternLoader

__all__ = [
    "Pattern",
    "PatternDef",
    "GroupEffect",
    "ColorPalette",
    "HSV",
    "PatternLoader",
]
