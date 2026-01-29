"""
DSL (Domain Specific Language) components for Strudel patterns.

Provides pattern constructors and mini-notation parsing.
"""

from .constructors import light, stack, cat, all_lights, sequence, ceiling, perimeter
from .parser import parse_mini, parse_to_query_data, ParsedEvent

__all__ = [
    # Constructors
    "light",
    "stack",
    "cat",
    "all_lights",
    "sequence",
    "ceiling",
    "perimeter",
    # Parser
    "parse_mini",
    "parse_to_query_data",
    "ParsedEvent",
]
