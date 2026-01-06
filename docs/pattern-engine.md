# Strudel Pattern System

> **Purpose**: This document covers the Strudel-inspired pattern language for creating lighting effects.

## Overview

The Strudel pattern system provides a composable, functional approach to creating lighting patterns. Inspired by the Strudel/TidalCycles live coding language, patterns are built by chaining transformations together.

Key concepts:
- **LightPattern**: A function that generates lighting events over time
- **Mini notation**: Shorthand syntax for creating patterns (`"all"`, `"left right"`)
- **Transformations**: Chainable methods that modify patterns (`fast()`, `shuffle()`, `color()`)
- **Envelopes**: ADSR-style intensity curves for flash-and-fade effects
- **Composition**: Combine patterns with `stack()` (parallel) and `cat()` (sequence)

## Core Constructors

### `light(notation)` - Create a Pattern

The main entry point for creating patterns:

```python
from dj_hue.patterns.strudel import light

# Target all lights for the full cycle
light("all")

# Sequence through lights (each gets 1/4 of the cycle)
light("0 1 2 3")

# Target groups
light("left right")    # Left half, then right half
light("odd even")      # Odd lights, then even lights

# Rest notation (silence)
light("all ~")         # All on, then off (half and half)
light("all ~*3")       # All on for 1/4, rest for 3/4
light("all ~*15")      # Flash on beat 1, rest for 15/16ths
```

### `stack(*patterns)` - Layer Patterns

Play multiple patterns simultaneously:

```python
from dj_hue.patterns.strudel import light, stack

# Red on left, blue on right, both at same time
stack(
    light("left").color("red"),
    light("right").color("blue"),
)

# Base ambient layer with flash overlay
stack(
    light("all").color("orange").intensity(0.3),  # Ambient base
    light("all ~*15").color("white"),              # Flash on beat 1
)
```

### `cat(*patterns)` - Sequence Patterns

Play patterns one after another (each gets one cycle):

```python
from dj_hue.patterns.strudel import light, cat

# Each pattern plays for one bar, then repeats
cat(
    light("all").color("red"),
    light("all").color("blue"),
    light("all").color("green"),
)

# Strobe build: doubles speed each cycle
cat(
    light("all ~").fast(2),   # Quarter notes
    light("all ~").fast(4),   # 8th notes
    light("all ~").fast(8),   # 16th notes
    light("all ~").fast(16),  # 32nd notes
)
```

## Mini Notation

The mini notation is a shorthand for specifying which lights to target and when:

| Notation | Meaning |
|----------|---------|
| `"all"` | All lights, full cycle |
| `"left"` | Left group, full cycle |
| `"right"` | Right group, full cycle |
| `"odd"` | Odd-indexed lights |
| `"even"` | Even-indexed lights |
| `"0 1 2 3"` | Sequence through lights 0, 1, 2, 3 |
| `"~"` | Rest/silence |
| `"~*3"` | Rest for 3 time units |
| `"all ~"` | All on for half, off for half |
| `"all all all all"` | All lights, 4 times per cycle (beats) |

## Transformations

All transformations return new patterns (immutable/functional style).

### Time Transforms

```python
pattern = light("all")

# Speed up/slow down
pattern.fast(2)      # 2x speed (plays twice per cycle)
pattern.fast(4)      # 4x speed (16th notes if base is quarter)
pattern.slow(2)      # Half speed (takes 2 cycles)

# Shift in time
pattern.early(0.25)  # Start 1/4 cycle earlier
pattern.late(0.5)    # Start 1/2 cycle later
```

### Structural Transforms

```python
# Sequence through individual lights in a group
light("all").seq()              # Each light gets equal time
light("all").seq(slots=16)      # 16th note timing (16 slots per cycle)
light("all").seq(per_group=False)  # Sequence ALL lights together

# Shuffle order (deterministic per cycle)
light("all").seq().shuffle()

# Reverse within each cycle
light("all").seq().rev()
```

### Value Transforms

```python
# Set color
pattern.color("red")           # Named color
pattern.color("cyan")          # Named color
pattern.color(HSV(0.5, 1, 1))  # HSV tuple

# Flash and fade colors (used with envelopes)
pattern.color(flash="white", fade="red")

# Set intensity
pattern.intensity(0.5)         # 50% brightness
```

### Envelopes

ADSR-style envelopes control how intensity varies over each event:

```python
# Quick flash, slow fade to 50%
pattern.envelope(attack=0.05, fade=1.0, sustain=0.5)

# Full ADSR
pattern.envelope(
    attack=0.1,   # Ramp up time (cycles)
    decay=0.2,    # Ramp down to sustain (cycles)
    sustain=0.5,  # Hold level (0-1)
    release=0.1,  # Fade out after event (cycles)
)

# Envelope with color transitions
pattern.envelope(attack=0.02, fade=0.5).color(flash="white", fade="orange")
```

## Examples

### Beat Flash
All lights flash on each beat:
```python
beat_flash = (
    light("all all all all")  # 4 events per cycle
    .envelope(attack=0.02, fade=0.2)
    .color(flash="white", fade="cyan")
)
```

### Smooth Chase
Lights sequence around with smooth transitions:
```python
smooth_chase = (
    light("all")
    .seq()
    .envelope(attack=0.1, fade=0.3, sustain=0.2)
    .color("cyan")
)
```

### Stagger Flash
Random sequence through all lights, white flash fading to red:
```python
stagger_flash = (
    light("all")
    .seq(per_group=False)  # All lights together
    .shuffle()
    .envelope(attack=0.05, fade=1.0, sustain=0.5)
    .color(flash="white", fade="red")
)
```

### Left/Right Alternating
```python
alternating = stack(
    light("left ~").color("red"),
    light("~ right").color("blue"),
)
```

### Strobe Build
Strobe that doubles speed every 2 bars:
```python
strobe_build = (
    cat(
        light("all ~").fast(2),   # Quarter notes
        light("all ~").fast(4),   # 8th notes
        light("all ~").fast(8),   # 16th notes
        light("all ~").fast(16),  # 32nd notes
    )
    .slow(2)  # Each step gets 2 bars
    .color("white")
)
```

### Green Cascade
Alternating even/odd pulse with sequential flash overlay:
```python
green_cascade = stack(
    # Even lights on beats 1, 3
    light("even ~ even ~").envelope(attack=0.02, fade=0.2).color("lime"),
    # Odd lights on beats 2, 4
    light("~ odd ~ odd").envelope(attack=0.02, fade=0.2).color("lime"),
    # Sequential white flash through ALL lights
    light("all")
        .seq(slots=16, per_group=False)
        .envelope(attack=0.01, fade=0.12)
        .color(flash="white", fade="lime"),
)
```

## Presets

The system includes many ready-to-use patterns in `strudel/presets.py`:

| Name | Description |
|------|-------------|
| `s_stagger` | Random sequential white flash, fades to red |
| `s_beat_flash` | All lights flash on each beat |
| `s_downbeat` | Flash on beat 1 only |
| `s_chase_smooth` | Lights chase smoothly around |
| `s_chase_fast` | Quick chase, 4x per bar |
| `s_chase_bounce` | Chase bounces back and forth |
| `s_strobe` | 16th note white strobe |
| `s_strobe_build` | Strobe speeds up over 8 bars |
| `s_gentle` | Slow ambient pulse |
| `s_color_wash` | Slow color cycling across lights |
| `s_alternate` | Left/right alternating |
| `s_random_pop` | Random lights pop on each beat |
| `s_green_cascade` | Neon green with sequential white flash |
| `s_blue_fade_strobe` | 2 beats fade, 2 beats strobe |

Load presets into the engine:
```python
from dj_hue.patterns.strudel import get_strudel_presets

presets = get_strudel_presets()
for name, (pattern, description) in presets.items():
    engine.register_strudel_pattern(name, pattern, description)
```

## Named Colors

Available color names:

| Name | HSV |
|------|-----|
| `white` | (0, 0, 1) |
| `red` | (0, 1, 1) |
| `orange` | (0.08, 1, 1) |
| `yellow` | (0.16, 1, 1) |
| `lime` | (0.25, 1, 1) |
| `green` | (0.33, 1, 1) |
| `cyan` | (0.5, 1, 1) |
| `blue` | (0.66, 1, 1) |
| `purple` | (0.75, 1, 1) |
| `magenta` | (0.83, 1, 1) |
| `pink` | (0.9, 0.6, 1) |

## Timing Reference

One **cycle** = one **bar** = 4 beats (in 4/4 time)

| Timing | Cycles | Example |
|--------|--------|---------|
| Whole note | 1.0 | `light("all")` |
| Half note | 0.5 | `light("all ~")` |
| Quarter note | 0.25 | `light("all all all all")` |
| 8th note | 0.125 | `light("all").fast(2)` per beat |
| 16th note | 0.0625 | `light("all ~").fast(16)` |

## Integration with PatternEngine

Register Strudel patterns with the engine:

```python
from dj_hue.patterns import PatternEngine
from dj_hue.patterns.strudel import light

engine = PatternEngine()

# Register a custom Strudel pattern
my_pattern = light("all").seq().shuffle().color("cyan")
engine.register_strudel_pattern("my_chase", my_pattern, "Custom chase pattern")

# Select the pattern
engine.set_pattern("my_chase")

# In render loop
colors = engine.compute_colors()
```

## Classic Pattern System

The older Pattern/GroupEffect/Phaser system is still available for backwards compatibility:

```python
from dj_hue.patterns import Pattern, GroupEffect, Phaser, ColorPalette, HSV

pattern = Pattern(
    name="Classic Pulse",
    group_effects=[
        GroupEffect(
            group_name="all",
            intensity_phaser=Phaser(waveform="sine", beats_per_cycle=2.0),
            color_index=0,
        ),
    ],
    default_palette=ColorPalette(colors=[HSV(0, 1, 1)]),
)
```

However, the Strudel system is recommended for new patterns as it's more expressive and composable.

## Related Files

- `src/dj_hue/patterns/strudel/` - Strudel pattern system
- `src/dj_hue/patterns/strudel/presets.py` - Pre-built patterns
- `src/dj_hue/patterns/engine.py` - PatternEngine
- `src/dj_hue/patterns/pattern_def.py` - Classic Pattern system
