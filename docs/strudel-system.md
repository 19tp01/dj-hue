# Strudel Pattern System

> **Purpose**: Comprehensive documentation of the dj-hue Strudel pattern system, including architectural philosophy, comparison with the original Strudel/TidalCycles, and complete technical reference.

## Overview

The dj-hue Strudel system is a **pattern language for lighting control**, inspired by [Strudel](https://strudel.cc) and [TidalCycles](https://tidalcycles.org). It brings the expressive power of live-coding music patterns to Philips Hue lights, enabling beat-synchronized, composable lighting effects.

**Key Features:**
- **Functional patterns** - Immutable, composable transformations
- **Query-based evaluation** - Patterns are functions from time to events
- **Mini notation** - Concise syntax for light targeting (`"all"`, `"left right"`)
- **ADSR envelopes** - Flash-and-fade intensity curves
- **Precise timing** - Fraction-based cycles without floating-point drift

---

## Architectural Philosophy

### Patterns as Pure Functions

The core insight from TidalCycles is that **a pattern is a function**:

```python
# A pattern IS a query function
QueryFunc = Callable[[TimeSpan, LightContext], list[LightHap]]
```

Given a time span to query and a context (which lights exist, how they're grouped), a pattern returns all events occurring in that window. This is fundamentally different from imperative approaches where you might iterate through time steps and mutate state.

**Why this matters:**
- **Lazy evaluation**: Only compute events you need
- **Infinite patterns**: Query any time range—patterns extend infinitely
- **Deterministic**: Same query always returns same events
- **Composable**: Transformations wrap queries, building complex patterns from simple ones

### Query-Based Evaluation

When the scheduler needs colors for frame N, it:
1. Converts frame time to a beat position
2. Queries the pattern for events in a small time window
3. Applies envelopes and modulators
4. Returns RGB colors for each light

```
scheduler.compute_colors(beat_position=12.5)
    ↓
pattern.query(TimeSpan(12.25, 12.75), context)
    ↓
[LightHap(light=0, color=cyan), LightHap(light=1, color=red), ...]
    ↓
{0: RGB(0, 255, 255), 1: RGB(255, 0, 0), ...}
```

### The Hap Concept

A **Hap** (happening) is an event with timing. Each LightHap has:
- **whole**: The complete logical duration of this event
- **part**: The portion visible in the current query window
- **value**: Light properties (ID, color, intensity, envelope)

The whole/part distinction is crucial for envelopes:
```
Event whole:  |=============================|
Query window:        |---------|
Event part:          |---------|

The envelope uses 'whole' to calculate intensity at any point,
even when we only query a small window.
```

### Immutable Transformations

All pattern methods return **new patterns**:

```python
base = light("all")
faster = base.fast(2)      # New pattern, base unchanged
colored = faster.color("cyan")  # Another new pattern
```

This enables:
- Safe composition (no side effects)
- Easy experimentation (original patterns unchanged)
- Predictable behavior (no hidden state)

### Cycle-Based Timing

Time is measured in **cycles**, where:
- 1 cycle = 1 bar = 4 beats (in 4/4 time)
- Uses Python's `Fraction` for exact arithmetic

```python
TimeSpan(Fraction(0), Fraction(1))      # First bar
TimeSpan(Fraction(1, 4), Fraction(1, 2))  # Second quarter note
```

Fractions prevent floating-point accumulation errors over long sessions—essential for tight beat sync.

---

## Comparison with Original Strudel

### Overview

| Aspect | Original Strudel | dj-hue Strudel |
|--------|------------------|----------------|
| Language | JavaScript | Python |
| Output | Audio (WebAudio/SuperDirt) | RGB lighting (Hue Entertainment API) |
| Hap values | Note, synth params, effects | Light ID, color, intensity, envelope |
| Query method | `pattern.queryArc(0, 1)` | `pattern.query(TimeSpan, LightContext)` |
| Timing | Fraction-based cycles | Fraction-based cycles (identical) |
| Scheduler | Browser requestAnimationFrame | 50Hz render thread |
| Mini notation | PEG grammar parser | Custom tokenizer/parser |

### Shared Concepts

**Fraction-Based Timing:**
Both systems use exact fractions for cycle timing. This is a direct port of TidalCycles' approach, ensuring musical timing remains precise over arbitrarily long performances.

**Query Functions:**
The fundamental pattern type is identical—a function that maps time spans to events. Original Strudel:
```javascript
const haps = pattern.queryArc(0, 1);
```
dj-hue:
```python
haps = pattern.query(TimeSpan(0, 1), context)
```

**Haps with Whole/Part:**
Both track the logical event duration (`whole`) separately from the queried portion (`part`). This enables correct envelope behavior when events span query boundaries.

**Mini Notation Basics:**
Shared syntax elements:
- Spaces for sequencing: `"a b c"` → three events per cycle
- `~` for rest/silence
- `*n` for repetition: `"a*4"` → four events
- `/n` for slowing: `"a/2"` → spans two cycles

**Functional Transformations:**
Both systems use the same transformation pattern—functions that take a pattern and return a new pattern:
- `fast(n)` / `slow(n)` for tempo changes
- Pattern combinators for composition

### Adaptations for Lighting

**LightContext:**
Unlike audio where notes are abstract, lighting requires knowing which physical lights exist. `LightContext` provides:
```python
context = LightContext(
    num_lights=6,
    groups={"all": [0,1,2,3,4,5], "left": [0,1,2], "right": [3,4,5]},
)
```

Patterns are **portable**—they reference group names like `"left"`, and the context resolves these to actual light IDs at query time.

**Envelope System:**
Audio synths have built-in ADSR. For lighting, we added explicit envelope support:
```python
pattern.envelope(attack=0.05, fade=0.5, sustain=0.3)
       .color(flash="white", fade="red")
```

This creates the signature "flash and fade" effect—bright white attack, fading to colored sustain.

**Modulator System:**
LFO-style intensity modulation for breathing/pulsing effects:
```python
pattern.modulate("sine", frequency=2.0, min_intensity=0.5, max_intensity=1.0)
```

**Zone Awareness:**
Spatial patterns can target zones (ceiling, perimeter) with fallback behavior when zones aren't available.

### What We Didn't Port

**Nested Mini Notation:**
Original Strudel supports `"[a b] c"` for subdivision. We use flat notation with explicit transforms:
```python
# Instead of "[a b] c" (a and b in first half, c in second half)
light("left right").fast(2) + light("all").late(0.5)
```

**Pattern Algebra (Applicative/Monadic):**
Original Strudel has sophisticated pattern combination via `appLeft`, `appRight`, etc. We use simpler `stack()` and `cat()` combinators.

**Audio-Specific Features:**
No ports of audio effects, synthesis parameters, or MIDI output—these don't apply to lighting.

---

## Core Data Structures

### TimeSpan

Represents a time interval in cycles:

```python
@dataclass(frozen=True)
class TimeSpan:
    start: Fraction
    end: Fraction

    @property
    def duration(self) -> Fraction:
        return self.end - self.start

    def intersection(self, other: TimeSpan) -> TimeSpan | None:
        """Return overlapping portion, or None"""

    def shift(self, offset: Fraction) -> TimeSpan:
        """Return new span shifted by offset"""

    def scale(self, factor: Fraction) -> TimeSpan:
        """Return new span scaled by factor"""
```

### LightValue

Properties of a light event:

```python
@dataclass
class LightValue:
    light_id: int | None = None     # Specific light, or None for group
    group: str | None = None        # Group name (e.g., "left")
    color: HSV | None = None        # Target color
    intensity: float = 1.0          # Brightness multiplier (0.0-1.0)
    envelope: Envelope | None = None
    modulator: Modulator | None = None
```

### LightHap

A light "happening" with timing:

```python
@dataclass
class LightHap:
    whole: TimeSpan | None  # Full logical duration
    part: TimeSpan          # Portion in this query
    value: LightValue       # Light properties

    def whole_or_part(self) -> TimeSpan:
        """Return whole if available, else part"""
```

### LightContext

Runtime context for pattern evaluation:

```python
@dataclass
class LightContext:
    num_lights: int
    groups: dict[str, list[int]]  # Group name → light indices
    zones: dict[str, list[int]]   # Zone name → light indices
    cycle_beats: float = 4.0

    def resolve_group(self, name: str) -> list[int]:
        """Resolve group name to light indices"""

    @classmethod
    def default(cls, num_lights: int = 6) -> LightContext:
        """Create default context with standard groups"""
```

### LightPattern

The core pattern type:

```python
class LightPattern:
    def __init__(self, query_func: QueryFunc):
        self._query = query_func

    def query(self, span: TimeSpan, context: LightContext) -> list[LightHap]:
        """Query events within the given time span"""
        return self._query(span, context)

    # All transformation methods return new LightPatterns
    def fast(self, factor) -> LightPattern: ...
    def slow(self, factor) -> LightPattern: ...
    def color(self, color) -> LightPattern: ...
    # etc.
```

---

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
light("all ~")         # All on for half, off for half
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

---

## Mini Notation Reference

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

---

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

**How `fast()` works internally:**
```python
def fast(self, factor):
    def query_fast(span, ctx):
        # Query a larger time span
        expanded = TimeSpan(span.start * factor, span.end * factor)
        haps = self._query(expanded, ctx)
        # Compress results back
        return [h.scale(factor) for h in haps]
    return LightPattern(query_fast)
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

# Pick random lights (new pick per event)
light("all all all all").pick(1, 2)  # 1-2 random lights per beat
light("all").pick(0.5)               # 50% of lights

# Pick with hold (same pick for time window)
# IMPORTANT: .pick() must come AFTER .fast() so it sees scaled positions
light("all").fast(16).pick(1, hold=0.25)  # Same light strobes for 1 beat
light("all").pick(2, hold=1.0)            # Same 2 lights for entire bar
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

---

## Advanced Features

### Modulator (LFO)

Oscillating intensity modulation for breathing/pulsing effects:

```python
pattern.modulate(
    wave="sine",        # sine, triangle, saw, square
    frequency=1.0,      # Oscillations per bar
    min_intensity=0.5,  # Minimum brightness
    max_intensity=1.0,  # Maximum brightness
    phase=0.0,          # Phase offset (0.0-1.0)
)

# Examples:
# Gentle breathing
.modulate("sine", frequency=1.0, min_intensity=0.8, max_intensity=1.0)

# Fast pulsing
.modulate("square", frequency=4.0, min_intensity=0.5, max_intensity=1.0)

# Slow 2-bar breathe
.modulate("sine", frequency=0.5, min_intensity=0.6, max_intensity=1.0)
```

### Autonomous Patterns

Each light blinks independently at a random frequency:

```python
pattern.autonomous(
    min_freq=1.0,   # Minimum blinks per cycle/bar
    max_freq=4.0,   # Maximum blinks per cycle/bar
    duty=0.5,       # Fraction of time "on" (0.0-1.0)
    colors=["yellow", "orange"],  # Random color per blink
    seed=None,      # Optional seed for reproducibility
)
```

Parameters:
- `min_freq`, `max_freq`: Blinks per cycle/bar (each light picks a random frequency)
- `duty`: Duty cycle - fraction of time "on" (default 0.5)
- `colors`: Optional list of color names to randomly choose from per blink
- `seed`: Random seed for reproducibility (default: uses light_id)

The timing is pseudo-random but deterministic—same seed produces same pattern.

### Spatial/Zone Patterns

Zone-aware patterns for multi-area setups (e.g., ceiling + perimeter):

```python
# Patterns can target zones
ceiling_pattern = light("ceiling").color("blue")
perimeter_pattern = light("perimeter").color("red")

# Combine with fallback behavior
layered = stack(ceiling_pattern, perimeter_pattern)
```

See `docs/SPATIAL_PATTERNS_PROPOSAL.md` for detailed zone system documentation.

---

## Scheduler & Render Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  Pattern Definition                                              │
│  light("all").seq().shuffle().color("cyan")                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PatternScheduler.compute_colors(beat_position)                 │
│                                                                  │
│  1. Calculate query window around beat_position                 │
│  2. pattern.query(TimeSpan, context) → list[LightHap]          │
│  3. For each hap:                                               │
│     - Apply envelope at current time → intensity                │
│     - Apply modulator at current time → intensity               │
│     - Calculate final color                                      │
│  4. Resolve groups to light IDs                                 │
│  5. Return dict[light_id, RGB]                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Hue Entertainment API                                          │
│  Stream RGB colors to physical lights @ 50Hz                    │
└─────────────────────────────────────────────────────────────────┘
```

### PatternScheduler

The `PatternScheduler` bridges patterns to the render loop:

```python
from dj_hue.patterns.strudel import PatternScheduler

scheduler = PatternScheduler(pattern, context)

# In render loop (50Hz)
def render_frame(beat_position: float):
    colors = scheduler.compute_colors(beat_position)
    # colors: {0: RGB(255, 0, 0), 1: RGB(0, 255, 0), ...}
    send_to_hue(colors)
```

### Integration with BeatClock

The beat position comes from `BeatClock`, which syncs to either:
- **MIDI Clock** from Ableton (24 ticks per beat)
- **Audio beat detection** from microphone input

---

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

---

## Presets

Ready-to-use patterns in `strudel/presets.py`:

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
| `s_autonomous` | Each light random on/off timing |
| `s_fireflies` | Warm color random blinking |
| `s_rainbow_chase` | Rainbow colors on half notes |
| `s_rainbow_breathe` | Rainbow with sine wave breathing |

Load presets:
```python
from dj_hue.patterns.strudel import get_strudel_presets

presets = get_strudel_presets()
for name, (pattern, description) in presets.items():
    engine.register_strudel_pattern(name, pattern, description)
```

---

## Named Colors

**Primary colors:**
| Name | HSV |
|------|-----|
| `red` | (0, 1, 1) |
| `orange` | (0.08, 1, 1) |
| `yellow` | (0.16, 1, 1) |
| `lime` | (0.25, 1, 1) |
| `green` | (0.33, 1, 1) |
| `cyan` | (0.5, 1, 1) |
| `blue` | (0.6, 1, 1) |
| `purple` | (0.75, 1, 1) |
| `magenta` | (0.83, 1, 1) |
| `pink` | (0.9, 0.6, 1) |

**Whites and neutrals:**
| Name | HSV |
|------|-----|
| `white` | (0, 0, 1) |
| `warm_white` | (0.08, 0.2, 1) |
| `cool_white` | (0.55, 0.1, 1) |

**DJ-friendly colors:**
| Name | HSV |
|------|-----|
| `amber` | (0.1, 1, 1) |
| `teal` | (0.45, 1, 1) |
| `violet` | (0.7, 1, 1) |
| `hot_pink` | (0.92, 1, 1) |

**Dimmed variants:**
| Name | HSV |
|------|-----|
| `dim_red` | (0, 1, 0.5) |
| `dim_blue` | (0.6, 1, 0.5) |
| `dim_white` | (0, 0, 0.5) |

---

## Timing Reference

One **cycle** = one **bar** = 4 beats (in 4/4 time)

| Timing | Cycles | Example |
|--------|--------|---------|
| Whole note | 1.0 | `light("all")` |
| Half note | 0.5 | `light("all ~")` |
| Quarter note | 0.25 | `light("all all all all")` |
| 8th note | 0.125 | `light("all").fast(2)` per beat |
| 16th note | 0.0625 | `light("all ~").fast(16)` |

---

## Design Decisions

### Why Query-Based (vs Imperative)

Imperative approach:
```python
# Problematic: requires iteration, state management
for beat in range(total_beats):
    if beat % 4 == 0:
        turn_on_light(0)
    else:
        turn_off_light(0)
```

Query-based approach:
```python
# Clean: pattern IS the definition
pattern = light("all ~*3")  # On for 1/4, off for 3/4

# Query any window, get events
haps = pattern.query(TimeSpan(100, 101), context)  # Works for cycle 100
```

Benefits:
- **Matches musical thinking**: Musicians think in terms of time spans, not procedural steps
- **Enables transformations**: `fast()`, `slow()`, `shuffle()` work by modifying queries
- **Supports partial queries**: Only compute what you need

### Why Fraction Timing (vs Float)

```python
# Float accumulation error
0.1 + 0.1 + 0.1 == 0.3  # False! (0.30000000000000004)

# Fraction is exact
Fraction(1, 10) + Fraction(1, 10) + Fraction(1, 10) == Fraction(3, 10)  # True
```

Over a 4-hour DJ set at 128 BPM, floating-point drift could cause noticeable timing errors. Fractions stay perfectly aligned.

### Why Runtime Group Resolution

Patterns reference groups by name (`"left"`, `"all"`), not light IDs:

```python
# This pattern works with any setup
pattern = light("left").color("red")

# Resolution happens at query time
haps = pattern.query(span, context_with_6_lights)
haps = pattern.query(span, context_with_12_lights)
```

Benefits:
- **Portable patterns**: Same pattern works across setups
- **Dynamic discovery**: Add lights without redefining patterns
- **Zone fallback**: Patterns can degrade gracefully if zones are unavailable

### Why Python (vs JavaScript)

The original Strudel is JavaScript for browser-based live coding. dj-hue uses Python because:
- **Integration with audio analysis**: Python ecosystem for audio (librosa, numpy)
- **Raspberry Pi deployment**: Python runs easily on embedded devices
- **Hue SDK**: Python SDK for Hue Entertainment API
- **Developer preference**: The project already used Python for other components

---

## Classic Pattern System

The older Pattern/GroupEffect/Phaser system remains available for backwards compatibility:

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

However, the **Strudel system is recommended** for new patterns as it's more expressive and composable.

---

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

---

## Related Files

| File | Purpose |
|------|---------|
| `src/dj_hue/patterns/strudel/` | Strudel pattern system root |
| `src/dj_hue/patterns/strudel/core/pattern.py` | LightPattern class |
| `src/dj_hue/patterns/strudel/core/types.py` | TimeSpan, LightHap, LightValue, LightContext |
| `src/dj_hue/patterns/strudel/core/envelope.py` | ADSR envelope system |
| `src/dj_hue/patterns/strudel/dsl/parser.py` | Mini notation parser |
| `src/dj_hue/patterns/strudel/dsl/constructors.py` | `light()`, `stack()`, `cat()` |
| `src/dj_hue/patterns/strudel/scheduler.py` | PatternScheduler |
| `src/dj_hue/patterns/strudel/modulator.py` | LFO modulation |
| `src/dj_hue/patterns/presets/strudel_presets.py` | Pre-built patterns |
| `src/dj_hue/patterns/engine.py` | PatternEngine |

---

## Further Reading

- [Original Strudel](https://strudel.cc) - Browser-based live coding
- [TidalCycles](https://tidalcycles.org) - The Haskell original
- [Strudel Technical Manual](https://strudel.cc/technical-manual/patterns/) - Pattern internals
