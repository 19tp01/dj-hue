# Scene System

> **Purpose**: This document covers the scene system for organizing and switching patterns during live sets.

## Overview

Scenes are the primary way to control lighting during a live set. The current implementation provides:
- Pattern selection via keyboard (1-9 keys)
- Next/previous navigation (`[` and `]` keys)
- Quick actions (flash, blackout)

## Current Implementation

### Pattern Selection

The PatternEngine maintains a list of available patterns and supports selection by index:

```python
# Select by index (0-based)
engine.set_pattern_by_index(0)  # First pattern
engine.set_pattern_by_index(3)  # Fourth pattern

# Select by name
engine.set_pattern("s_chase_smooth")

# Navigation
engine.next_pattern()
engine.prev_pattern()
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `1-9` | Select pattern 1-9 |
| `0` | Select pattern 10 |
| `[` | Previous pattern |
| `]` | Next pattern |
| `Space` | Toggle blackout |
| `f` | Flash (momentary white) |
| `r` | Reset beat position |
| `h` | Show help |
| `q` | Quit |

### Quick Actions

Momentary effects that don't change the current pattern:

```python
from dj_hue.patterns import QuickAction

# Flash all lights white
engine.trigger_quick_action(QuickAction.flash(duration_beats=0.5))

# Toggle blackout
engine.toggle_blackout()
```

## Future: Scene Data Structure

A more complete scene system could include:

```python
@dataclass
class Scene:
    name: str
    pattern_name: str

    # Modifiers
    intensity_scale: float = 1.0  # 0.0-2.0, multiplier for brightness
    speed_scale: float = 1.0      # 0.5 = half speed, 2.0 = double speed
    hue_shift: float = 0.0        # 0.0-1.0, shifts all colors

    # Tags for organization/auto-pilot
    tags: list[str] = field(default_factory=list)
```

### Scene Modifiers

**intensity_scale**: Multiplies all brightness values
- 0.5 = dim, intimate
- 1.0 = normal
- 1.5 = bright, energetic

**speed_scale**: Multiplies pattern speed
- 0.5 = half speed
- 1.0 = normal
- 2.0 = double speed

**hue_shift**: Shifts all colors around the color wheel
- 0.0 = no shift
- 0.5 = complementary colors

### Example Scene Bank

```python
scenes = [
    Scene(name="Ambient", pattern_name="s_gentle", intensity_scale=0.6, tags=["intro", "chill"]),
    Scene(name="Groove", pattern_name="s_chase_smooth", tags=["verse"]),
    Scene(name="Build", pattern_name="s_strobe_build", tags=["build"]),
    Scene(name="Drop", pattern_name="s_stagger", tags=["drop", "peak"]),
    Scene(name="Breakdown", pattern_name="s_color_wash", intensity_scale=0.4, tags=["breakdown"]),
]
```

## Ideas

### Scene Chains
Automatic progression through scenes:
```python
chain = [
    ("Build", 4),      # 4 bars
    ("Drop", 8),       # 8 bars
    ("Breakdown", 8),  # 8 bars
]
```

### Conditional Scenes
Scenes that activate based on conditions (e.g., energy threshold).

### Scene Persistence
Save/load scene banks to YAML files.

## Related Files

- `src/dj_hue/patterns/engine.py` - PatternEngine with pattern selection
- `src/dj_hue/midi_pattern_mode.py` - Keyboard handling
