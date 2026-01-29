"""
CLI entry points for dj-hue.

Contains the main executable scripts:
- link_hue: Ableton Link synchronized light control
- midi_hue: MIDI Clock based light control with effects
- midi_pattern_mode: Full pattern engine with hot-reload
"""

from .midi_pattern_mode import main as pattern_main
from .midi_hue import main as midi_main
from .link_hue import main as link_main

__all__ = [
    "pattern_main",
    "midi_main",
    "link_main",
]
