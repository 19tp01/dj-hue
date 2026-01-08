"""
Core types for the Strudel pattern system.

Provides fundamental data structures:
- TimeSpan: Time intervals in cycles
- LightValue: Light event properties
- LightHap: Light events with timing
- LightContext: Runtime context
- LightPattern: Composable pattern type
- Envelope: ADSR-style intensity envelopes
"""

from .types import TimeSpan, LightHap, LightValue, LightContext
from .pattern import LightPattern
from .envelope import Envelope, interpolate_hsv

__all__ = [
    "TimeSpan",
    "LightHap",
    "LightValue",
    "LightContext",
    "LightPattern",
    "Envelope",
    "interpolate_hsv",
]
