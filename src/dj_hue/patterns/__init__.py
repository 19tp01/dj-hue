"""
Pattern engine for DJ-Hue.

This module provides the pattern engine with:
- Light grouping (zones like left/right, front/back)
- Strudel pattern system for composable effects
- Hot-reload capability

The pattern engine uses the Strudel system exclusively.
All patterns are LightPattern instances.
"""

from .common.groups import LightGroup, LightSetup, ZoneType
from .engine import PatternEngine, QuickAction

# Re-export core Strudel types
from .strudel import (
    # Core types
    HSV,
    LightPattern,
    LightContext,
    TimeSpan,
    LightHap,
    LightValue,
    Envelope,
    # Constructors
    light,
    stack,
    cat,
    ceiling,
    perimeter,
    # Scheduler
    PatternScheduler,
)

# Re-export decorator for user patterns
from .decorator import pattern

__all__ = [
    # Groups
    "LightGroup",
    "LightSetup",
    "ZoneType",
    # Core Strudel types
    "HSV",
    "LightPattern",
    "LightContext",
    "TimeSpan",
    "LightHap",
    "LightValue",
    "Envelope",
    # Constructors
    "light",
    "stack",
    "cat",
    "ceiling",
    "perimeter",
    # Scheduler
    "PatternScheduler",
    # Engine
    "PatternEngine",
    "QuickAction",
    # Decorator
    "pattern",
]
