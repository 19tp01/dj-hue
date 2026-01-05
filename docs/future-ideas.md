# Future Ideas

> **Purpose**: This document is for Claude Code to track ideas, TODOs, and future approaches for dj-hue features beyond the initial pattern engine.

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
        # Track energy trend over last N bars
        energy_trend = self.get_energy_trend()

        # Check for increasing high frequencies
        high_freq_rising = self.high_bands_increasing()

        # Rapid transient density (snare rolls)
        transient_density = self.get_transient_density()

        return combine(energy_trend, high_freq_rising, transient_density)
```

### Drop Handling Options

1. **Manual trigger** (implemented first)
   - DJ hits a button right before/on the drop
   - Most reliable, gives full control

2. **Build detection + timer**
   - Detect build, auto-trigger drop after ~16 bars
   - Works for formulaic EDM, fails for creative arrangements

3. **Build detection + manual confirm**
   - Detect "we're probably in a build"
   - Prepare intense pattern, DJ confirms with button

### Serato Integration Research

No official Serato API for playback position. Options explored:

| Tool | What it provides | Limitation |
|------|------------------|------------|
| [serato-dj-api](https://github.com/srinitude/serato-dj-api) | Track loaded events | No position |
| [Now Playing for Serato](https://github.com/e1miran/Now-Playing-Serato) | Current track name | No position |
| [djctl](https://www.djctl.com/docs/quickstart/serato/) | External control | 2 deck limit |

**Conclusion**: Pre-analyzed track cues would need manual triggering since we can't get playback position.

---

## GUI Design

### Requirements
- Auto-pilot driven with manual overrides
- Visual feedback of current pattern/scene
- Easy scene switching
- Works on small screen (tablet-sized)

### Layout Concept

```
┌─────────────────────────────────────────┐
│ BPM: 128    Beat: ████░░░░    Scene: 3  │
├─────────────────────────────────────────┤
│                                         │
│   [1]       [2]       [3]       [4]     │
│  Ambient   Groove    Build     Drop     │
│   ○         ○        ●active    ○       │
│                                         │
├─────────────────────────────────────────┤
│ Intensity: ═══════════░░░  Speed: 1.0x  │
│ Hue Shift: ░░░░░░░░░░░░░  [AUTO-PILOT]  │
└─────────────────────────────────────────┘
```

### Technology Options

| Option | Pros | Cons |
|--------|------|------|
| Terminal UI (rich/textual) | No deps, runs in terminal | Limited visuals |
| Web UI (FastAPI + React) | Modern, flexible | Complexity, latency |
| PyQt/PySide | Native, responsive | Heavy dependency |
| Dear ImGui (via imgui) | Game-style, fast | Learning curve |

### First Step: Terminal UI
Start with `rich` or `textual` for a terminal-based UI:
- Shows current BPM, beat position, scene
- Number key scene switching
- Intensity/speed sliders with arrow keys

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
    def __init__(self, scene_bank: SceneBank):
        self.scene_bank = scene_bank
        self.last_change = 0.0
        self.min_scene_duration = 16.0  # bars

    def suggest_scene(self, energy: float, bar_position: float) -> Optional[Scene]:
        # Don't change too frequently
        if bar_position - self.last_change < self.min_scene_duration:
            return None

        # Find scenes matching energy level
        candidates = [
            s for s in self.scene_bank.scenes
            if self._energy_matches(s, energy)
        ]

        # Weight by how long since last use
        return self._weighted_random(candidates)

    def _energy_matches(self, scene: Scene, energy: float) -> bool:
        # Match scene tags to energy
        if energy < 0.3:
            return "chill" in scene.tags or "ambient" in scene.tags
        elif energy < 0.6:
            return "verse" in scene.tags or "groove" in scene.tags
        elif energy < 0.8:
            return "build" in scene.tags
        else:
            return "drop" in scene.tags or "peak" in scene.tags
```

### Manual Override
- Any manual scene selection disables auto-pilot temporarily
- Re-enable with button or timeout
- Show "AUTO" indicator in UI

---

## Pattern Blending

### Crossfade Transitions
When switching scenes, blend between patterns:

```python
def compute_blended_colors(self) -> dict[int, RGB]:
    if self._blend_progress >= 1.0:
        return self._compute_pattern_colors(self._current_pattern)

    from_colors = self._compute_pattern_colors(self._blend_from)
    to_colors = self._compute_pattern_colors(self._current_pattern)

    blended = {}
    t = self._blend_progress
    for i in range(self.num_lights):
        blended[i] = RGB(
            int(from_colors[i].r * (1-t) + to_colors[i].r * t),
            int(from_colors[i].g * (1-t) + to_colors[i].g * t),
            int(from_colors[i].b * (1-t) + to_colors[i].b * t),
        )
    return blended
```

### Fade to Black
Alternative transition: fade out, then fade in:

```python
def fade_to_black_transition(progress: float) -> float:
    """0-0.5: fade out, 0.5-1.0: fade in"""
    if progress < 0.5:
        return 1.0 - (progress * 2)  # 1.0 -> 0.0
    else:
        return (progress - 0.5) * 2  # 0.0 -> 1.0
```

---

## Additional Waveforms

### Ideas for new waveforms

```python
def waveform_bounce(phase: float) -> float:
    """Bouncing ball effect - fast at bottom, slow at top"""
    return abs(math.sin(phase * math.pi))

def waveform_steps(phase: float, steps: int = 4) -> float:
    """Stepped/quantized output"""
    return math.floor(phase * steps) / (steps - 1)

def waveform_noise(phase: float, seed: int = 0) -> float:
    """Perlin-style smooth noise"""
    # Would need noise implementation
    pass

def waveform_custom(phase: float, points: list[float]) -> float:
    """User-defined curve via interpolation"""
    # Linear interpolation between points
    pass
```

---

## MIDI Controller Support

### Use Case
Physical MIDI controller (Launchpad, Push, etc.) for scene triggering.

### Implementation Sketch

```python
class MIDIController:
    def __init__(self, pattern_engine: PatternEngine):
        self.engine = pattern_engine
        self.port = mido.open_input('Launchpad', callback=self._on_message)

    def _on_message(self, msg):
        if msg.type == 'note_on':
            # Map note to scene
            scene_idx = self._note_to_scene(msg.note)
            self.engine.set_scene_by_index(scene_idx)

        elif msg.type == 'control_change':
            # Map CC to intensity/speed
            if msg.control == 1:  # Mod wheel
                self.engine.set_intensity_scale(msg.value / 127.0 * 2.0)
```

---

## Performance Optimization

### Current Bottleneck
Hue Entertainment API is limited to ~25-50 Hz. Beyond that, packets queue up.

### Ideas
- Predictive color computation (compute next few frames ahead)
- Adaptive frame rate based on pattern complexity
- Batch similar updates (if all lights same color, send once)

---

## Related Files

- `src/dj_hue/audio/beat.py` - Existing beat detection
- `src/dj_hue/audio/analyzer.py` - Frequency analysis
- `src/dj_hue/patterns/engine.py` - Pattern engine (to extend)
