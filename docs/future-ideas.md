# Future Ideas

> **Purpose**: This document tracks ideas and future approaches for dj-hue features.

## Completed Features

### Strudel Pattern System
The Strudel-inspired pattern language is now fully implemented:
- Mini notation parser (`"all"`, `"left right"`, `"0 1 2 3"`)
- Time transforms: `fast()`, `slow()`, `early()`, `late()`
- Structural transforms: `seq()`, `shuffle()`, `rev()`
- Combinators: `stack()`, `cat()`
- ADSR envelopes with flash/fade colors
- Named colors and transforms
- Pre-built pattern presets

See [pattern-engine.md](./pattern-engine.md) for full documentation.

---

## Build/Drop Detection

### The Challenge
True drop detection requires knowing the future - we can't know there's a drop until it happens. However, builds have detectable characteristics.

### Build Detection Approach (Real-time feasible)

Builds typically have:
- Rising energy over 4-16 bars
- Filter sweeps (high frequencies increasing)
- Drum rolls (rapid transients)
- Often a "riser" sound (rising pitch)

```python
class BuildDetector:
    def detect(self, audio_features: dict) -> float:
        """Return build intensity 0.0-1.0"""
        energy_trend = self.get_energy_trend()
        high_freq_rising = self.high_bands_increasing()
        transient_density = self.get_transient_density()
        return combine(energy_trend, high_freq_rising, transient_density)
```

### Drop Handling Options

1. **Manual trigger** (recommended)
   - DJ hits a button right before/on the drop
   - Most reliable, gives full control

2. **Build detection + timer**
   - Detect build, auto-trigger drop after ~16 bars
   - Works for formulaic EDM, fails for creative arrangements

---

## GUI Design

### Requirements
- Visual feedback of current pattern/scene
- Easy pattern switching
- BPM and beat position display
- Works on small screen (tablet-sized)

### Layout Concept

```
┌─────────────────────────────────────────┐
│ BPM: 128    Beat: ████░░░░    Scene: 3  │
├─────────────────────────────────────────┤
│                                         │
│   [1]       [2]       [3]       [4]     │
│  s_gentle  s_chase  s_stagger s_strobe  │
│   ○         ○        ●active    ○       │
│                                         │
├─────────────────────────────────────────┤
│ Intensity: ═══════════░░░  Speed: 1.0x  │
│ [BLACKOUT]  [FLASH]         [AUTO-PILOT]│
└─────────────────────────────────────────┘
```

### Technology Options

| Option | Pros | Cons |
|--------|------|------|
| Terminal UI (rich/textual) | No deps, runs in terminal | Limited visuals |
| Web UI (FastAPI + React) | Modern, flexible | Complexity, latency |
| PyQt/PySide | Native, responsive | Heavy dependency |

---

## Auto-Pilot System

### Concept
Auto-pilot selects scenes based on:
- Energy level of current music
- Time since last scene change
- Scene tags and weights

### Energy-Based Selection

```python
class AutoPilot:
    def __init__(self, scene_bank: list[Scene]):
        self.scenes = scene_bank
        self.min_scene_duration = 16.0  # bars

    def suggest_scene(self, energy: float, bar_position: float) -> Scene | None:
        if bar_position - self.last_change < self.min_scene_duration:
            return None

        # Match scene tags to energy level
        if energy < 0.3:
            candidates = [s for s in self.scenes if "chill" in s.tags]
        elif energy < 0.6:
            candidates = [s for s in self.scenes if "verse" in s.tags]
        elif energy < 0.8:
            candidates = [s for s in self.scenes if "build" in s.tags]
        else:
            candidates = [s for s in self.scenes if "drop" in s.tags]

        return self._weighted_random(candidates)
```

---

## Pattern Blending

### Crossfade Transitions
When switching patterns, blend between them:

```python
def compute_blended_colors(self) -> dict[int, RGB]:
    if self._blend_progress >= 1.0:
        return self._compute_current()

    from_colors = self._compute_from()
    to_colors = self._compute_current()

    t = self._blend_progress
    return {
        i: RGB(
            int(from_colors[i].r * (1-t) + to_colors[i].r * t),
            int(from_colors[i].g * (1-t) + to_colors[i].g * t),
            int(from_colors[i].b * (1-t) + to_colors[i].b * t),
        )
        for i in range(self.num_lights)
    }
```

---

## MIDI Controller Support

### Use Case
Physical MIDI controller (Launchpad, Push, etc.) for pattern triggering.

### Implementation Sketch

```python
class MIDIController:
    def __init__(self, pattern_engine: PatternEngine):
        self.engine = pattern_engine
        self.port = mido.open_input('Launchpad', callback=self._on_message)

    def _on_message(self, msg):
        if msg.type == 'note_on':
            scene_idx = self._note_to_scene(msg.note)
            self.engine.set_pattern_by_index(scene_idx)

        elif msg.type == 'control_change':
            if msg.control == 1:  # Mod wheel
                self.engine.set_intensity_scale(msg.value / 127.0 * 2.0)
```

---

## Additional Ideas

### New Strudel Transforms
- `mirror()` - Mirror pattern (like bounce but symmetric)
- `degrade(probability)` - Randomly drop events
- `every(n, transform)` - Apply transform every N cycles
- `struct(pattern)` - Use another pattern as rhythmic structure

### Pattern Parameters
Expose pattern parameters that can be adjusted at runtime:
```python
pattern = light("all").seq().speed(param("chase_speed", default=1.0, min=0.5, max=4.0))
```

### Audio-Reactive Modulation
Optional audio reactivity on top of beat-sync:
```python
pattern.audio_mod(band="bass", target="intensity", amount=0.3)
```

---

## Related Files

- `src/dj_hue/audio/beat.py` - Existing beat detection
- `src/dj_hue/patterns/engine.py` - PatternEngine
- `src/dj_hue/patterns/strudel/` - Strudel pattern system
