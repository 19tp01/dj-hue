# Scene System

> **Purpose**: This document is for Claude Code to track ideas, TODOs, and implementation approaches for the scene system.

## Overview

Scenes are the primary way to control lighting during a live set. A scene combines:
- A pattern (the lighting effect)
- Modifiers (speed, intensity, hue shift)
- Transition settings

## Core Data Structures

### Scene

```python
@dataclass
class Scene:
    name: str
    pattern_name: str

    # Modifiers
    intensity_scale: float = 1.0  # 0.0-2.0, multiplier for brightness
    speed_scale: float = 1.0      # 0.5 = half speed, 2.0 = double speed
    hue_shift: float = 0.0        # 0.0-1.0, shifts all colors

    # Transition settings
    transition: SceneTransition = field(default_factory=SceneTransition)

    # Tags for organization/auto-pilot
    tags: list[str] = field(default_factory=list)
```

### SceneTransition

```python
@dataclass
class SceneTransition:
    duration_beats: float = 4.0
    style: str = "crossfade"  # crossfade, cut, fade_to_black
```

### SceneBank

Collection of scenes for a set:

```python
@dataclass
class SceneBank:
    name: str
    scenes: list[Scene] = field(default_factory=list)

    def get_scene(self, name: str) -> Optional[Scene]
    def get_scene_by_index(self, idx: int) -> Optional[Scene]
```

## Manual Switching

The primary interaction model for now:

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| 1-9 | Activate scene 1-9 |
| 0 | Activate scene 10 |
| [ | Previous scene |
| ] | Next scene |
| Space | Blackout toggle |
| Enter | Flash (momentary white) |

### Example Scene Bank

```python
scene_bank = SceneBank(
    name="house_set",
    scenes=[
        Scene(name="Ambient", pattern_name="warm_pulse", intensity_scale=0.6, tags=["intro", "chill"]),
        Scene(name="Groove", pattern_name="slow_wave", tags=["verse"]),
        Scene(name="Build", pattern_name="chase", speed_scale=1.5, tags=["build"]),
        Scene(name="Drop", pattern_name="strobe", tags=["drop", "peak"]),
        Scene(name="Breakdown", pattern_name="sine_wave", intensity_scale=0.4, tags=["breakdown"]),
    ]
)
```

## Scene Modifiers

### intensity_scale
Multiplies all brightness values:
- 0.5 = dim, intimate
- 1.0 = normal
- 1.5 = bright, energetic
- 2.0 = maximum (clips at 1.0)

### speed_scale
Multiplies the beat position for phasers:
- 0.5 = half speed (patterns take twice as long)
- 1.0 = normal
- 2.0 = double speed (patterns complete in half the time)

### hue_shift
Shifts all colors around the color wheel:
- 0.0 = no shift
- 0.5 = complementary colors
- Useful for changing mood without changing pattern

## TODO

- [ ] Implement Scene dataclass
- [ ] Implement SceneTransition dataclass
- [ ] Implement SceneBank class
- [ ] Add keyboard shortcuts for scene switching
- [ ] Implement crossfade transitions
- [ ] Add scene persistence (save/load banks)

## Ideas

### Quick Actions
Momentary effects that don't change the scene:
- Flash: All lights white for 1 beat
- Blackout: All lights off until released
- Freeze: Hold current colors
- Color bump: Shift hue momentarily

### Scene Chains
Automatic progression through scenes:
```python
chain = SceneChain([
    ChainStep(scene="Build", duration_bars=4),
    ChainStep(scene="Drop", duration_bars=8),
    ChainStep(scene="Breakdown", duration_bars=8),
])
```

### Conditional Scenes
Scenes that activate based on conditions:
```python
Scene(
    name="Auto-Drop",
    pattern_name="strobe",
    trigger=Trigger(
        type="energy_threshold",
        value=0.8,
        duration_beats=2,  # Must sustain for 2 beats
    )
)
```

## Related Files

- `src/dj_hue/patterns/scenes.py` - Implementation (to create)
- `src/dj_hue/main.py` - Keyboard handling
- `config.yaml` - Scene bank definitions
