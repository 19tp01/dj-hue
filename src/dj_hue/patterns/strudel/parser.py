"""
Mini notation parser for the Strudel pattern system.

Parses strings like "0 1 2", "all ~*15", "left right" into
structured event definitions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterator


# Known group names
GROUPS = {"all", "left", "right", "odd", "even", "front", "back", "center"}


@dataclass
class ParsedEvent:
    """A single parsed event from mini notation."""
    start: Fraction      # Start time (0-1 within cycle)
    end: Fraction        # End time (0-1 within cycle)
    light_id: int | None  # Specific light index, or None for group
    group: str | None    # Group name, or None for specific light
    is_rest: bool = False  # True if this is a rest (~)

    @property
    def duration(self) -> Fraction:
        return self.end - self.start


def parse_mini(notation: str) -> list[ParsedEvent]:
    """
    Parse mini notation string into a list of events.

    Supported syntax:
    - Numbers: specific light indices (0, 1, 2, etc.)
    - Groups: all, left, right, odd, even
    - Rest: ~ (silence/black)
    - Repeat: *n (repeat n times)
    - Slow: /n (stretch over n cycles)
    - Spaces: sequence elements

    Examples:
        "0 1 2"      -> lights 0, 1, 2 in sequence
        "all"        -> all lights for full cycle
        "all ~*15"   -> all lights once, then 15 rests (16th note flash)
        "left right" -> left half cycle, right half cycle

    Returns:
        List of ParsedEvent objects
    """
    tokens = tokenize(notation)
    if not tokens:
        return []

    events = parse_sequence(tokens, Fraction(0), Fraction(1))
    # Filter out rests for the return value (they're timing markers)
    return events


def tokenize(notation: str) -> list[str]:
    """
    Tokenize mini notation into a list of tokens.

    Handles: numbers, group names, ~, *n, /n, spaces
    """
    tokens = []
    i = 0
    s = notation.strip()

    while i < len(s):
        # Skip whitespace but mark as separator
        if s[i].isspace():
            while i < len(s) and s[i].isspace():
                i += 1
            if tokens and tokens[-1] != ' ':
                tokens.append(' ')
            continue

        # Rest
        if s[i] == '~':
            tokens.append('~')
            i += 1
            continue

        # Modifier: *n or /n
        if s[i] in '*/' and i + 1 < len(s):
            j = i + 1
            while j < len(s) and (s[j].isdigit() or s[j] == '.'):
                j += 1
            if j > i + 1:
                tokens.append(s[i:j])
                i = j
                continue
            # Just the operator without number
            tokens.append(s[i])
            i += 1
            continue

        # Number
        if s[i].isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            tokens.append(s[i:j])
            i = j
            continue

        # Word (group name)
        if s[i].isalpha() or s[i] == '_':
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == '_'):
                j += 1
            tokens.append(s[i:j])
            i = j
            continue

        # Unknown character, skip
        i += 1

    # Remove trailing space
    if tokens and tokens[-1] == ' ':
        tokens.pop()

    return tokens


def parse_sequence(
    tokens: list[str],
    start: Fraction,
    end: Fraction,
) -> list[ParsedEvent]:
    """
    Parse a sequence of tokens into events.

    Divides the time span evenly among top-level elements.
    Elements with *n modifiers count as n slots for timing purposes.
    """
    # Split by spaces to get top-level elements
    elements = split_by_space(tokens)
    if not elements:
        return []

    # Count total slots, accounting for *n modifiers
    # e.g., "ceiling ceiling ~*2" = 1 + 1 + 2 = 4 slots
    total_slots = 0
    element_slots = []
    for element in elements:
        slots = 1
        if len(element) > 1 and element[1].startswith('*'):
            try:
                slots = int(element[1][1:])
            except ValueError:
                try:
                    slots = int(float(element[1][1:]))
                except ValueError:
                    slots = 1
        element_slots.append(slots)
        total_slots += slots

    duration = end - start
    slot_duration = duration / total_slots

    events = []
    current_slot = 0
    for element, slots in zip(elements, element_slots):
        slot_start = start + slot_duration * current_slot
        slot_end = slot_start + slot_duration * slots
        events.extend(parse_element(element, slot_start, slot_end))
        current_slot += slots

    return events


def split_by_space(tokens: list[str]) -> list[list[str]]:
    """Split token list by space tokens."""
    if not tokens:
        return []

    elements: list[list[str]] = []
    current: list[str] = []

    for token in tokens:
        if token == ' ':
            if current:
                elements.append(current)
                current = []
        else:
            current.append(token)

    if current:
        elements.append(current)

    return elements


def parse_element(
    tokens: list[str],
    start: Fraction,
    end: Fraction,
) -> list[ParsedEvent]:
    """
    Parse a single element (value with optional modifier).

    Handles: number, group name, ~, and *n / /n modifiers
    """
    if not tokens:
        return []

    # Get base value and modifier
    value_token = tokens[0]
    modifier = None
    if len(tokens) > 1:
        modifier = tokens[1]

    # Parse the base value
    is_rest = value_token == '~'
    light_id = None
    group = None

    if is_rest:
        pass  # Rest, no light
    elif value_token.isdigit():
        light_id = int(value_token)
    elif value_token.lower() in GROUPS:
        group = value_token.lower()
    else:
        # Unknown, treat as group
        group = value_token.lower()

    # Apply modifier
    if modifier:
        if modifier.startswith('*'):
            # Repeat: expand into multiple events
            try:
                repeat_count = int(modifier[1:])
            except ValueError:
                repeat_count = int(float(modifier[1:]))

            if repeat_count > 0:
                sub_duration = (end - start) / repeat_count
                events = []
                for i in range(repeat_count):
                    sub_start = start + sub_duration * i
                    sub_end = sub_start + sub_duration
                    events.append(ParsedEvent(
                        start=sub_start,
                        end=sub_end,
                        light_id=light_id,
                        group=group,
                        is_rest=is_rest,
                    ))
                return events

        elif modifier.startswith('/'):
            # Slow: stretch over multiple cycles
            # This is handled at a higher level, just return normal event
            pass

    # Single event
    return [ParsedEvent(
        start=start,
        end=end,
        light_id=light_id,
        group=group,
        is_rest=is_rest,
    )]


def parse_to_query_data(notation: str) -> list[tuple[Fraction, Fraction, int | None, str | None]]:
    """
    Parse notation and return data suitable for creating a query function.

    Returns list of (start, end, light_id, group) tuples.
    Rests are filtered out.
    """
    events = parse_mini(notation)
    return [
        (e.start, e.end, e.light_id, e.group)
        for e in events
        if not e.is_rest
    ]
