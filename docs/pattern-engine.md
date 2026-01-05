# Pattern Engine Design

> **Purpose**: This document is for Claude Code to track ideas, TODOs, and implementation approaches for the pattern engine.

## Overview

The pattern engine extends the existing `EffectsEngine` from `effects.py` to add:
- Light group abstraction
- Declarative pattern definitions
- Scene modifiers (speed, intensity, hue shift)
- Hot-reload capability

## Core Data Structures

### PatternDef

The main pattern definition class:

```python
@dataclass
class PatternDef:
    name: str
    description: str
    author: str = "unknown"
    version: str = "1.0"
    tags: list[str] = field(default_factory=list)

    # Effects for each group
    group_effects: list[GroupEffect] = field(default_factory=list)

    # Optional: independent light effects (override group effects)
    independent_effects: dict[int, LightEffect] = field(default_factory=dict)

    # Metadata for GUI/selection
    energy_level: float = 0.5  # 0.0 = calm, 1.0 = intense
    color_scheme: str = "rainbow"
```

### GroupEffect

Effect applied to a named light group:

```python
@dataclass
class GroupEffect:
    group_name: str  # References LightGroup by name
    intensity_phaser: Phaser
    hue_phaser: Optional[Phaser] = None
    base_hue: float = 0.0
    saturation: float = 1.0
    phase_spread: bool = False  # Spread phase_offset across group members
```

## Example Pattern

```python
# patterns/warm_pulse.py
from dj_hue.patterns import PatternDef, GroupEffect, Phaser

pattern = PatternDef(
    name="Warm Pulse",
    description="Gentle pulsing in warm colors",
    author="DJ",
    tags=["chill", "warm", "ambient"],
    energy_level=0.3,

    group_effects=[
        GroupEffect(
            group_name="all",
            intensity_phaser=Phaser(
                waveform="sine",
                beats_per_cycle=2.0,
                min_value=0.3,
                max_value=1.0,
            ),
            base_hue=0.08,  # Orange
            saturation=0.9,
        ),
    ],
)
```

## Rendering Pipeline

```
1. Scene selection (manual)
     ↓
2. Get PatternDef from current scene
     ↓
3. Apply scene modifiers (speed_scale, intensity_scale, hue_shift)
     ↓
4. For each GroupEffect:
   a. Resolve group_name → LightGroup → list of light indices
   b. For each light in group:
      - Calculate phase (with optional spread)
      - Get intensity from phaser
      - Get hue from base + optional hue_phaser
      - Generate RGB via HSV
     ↓
5. Apply independent_effects (overrides)
     ↓
6. Return dict[light_index, RGB]
```

## TODO

- [ ] Implement PatternDef dataclass
- [ ] Implement GroupEffect dataclass
- [ ] Implement PatternEngine.compute_colors()
- [ ] Convert existing Pattern factory methods to PatternDef format
- [ ] Add pattern blending for transitions (future)

## Ideas

### Pattern Layers
Could support multiple patterns layered together:
- Base layer: ambient background
- Accent layer: beat-synced pulses
- Override layer: manual triggers (flash, blackout)

### Dynamic Parameters
Patterns could expose parameters that scenes can override:
```python
pattern = PatternDef(
    name="Chase",
    parameters={
        "speed": Parameter(default=1.0, min=0.5, max=4.0),
        "hue": Parameter(default=0.0, min=0.0, max=1.0),
    },
    ...
)
```

### Audio-Reactive Modulation
Could add optional audio reactivity on top of beat-sync:
```python
GroupEffect(
    ...
    audio_modulation=AudioMod(
        band="bass",
        target="intensity",
        amount=0.3,  # Add up to 30% based on bass energy
    ),
)
```

## Related Files

- `src/dj_hue/lights/effects.py` - Core Phaser, BeatClock, RGB
- `src/dj_hue/patterns/pattern_def.py` - PatternDef, GroupEffect (to create)
- `src/dj_hue/patterns/engine.py` - PatternEngine (to create)
