# DJ-Hue Pattern Engine Documentation

> **Purpose**: This documentation directory is for Claude Code to track ideas, TODOs, and implementation approaches for the dj-hue pattern engine system.

## Overview

DJ-Hue is a beat-synchronized lighting control system for Philips Hue lights, designed for live DJ performances. The pattern engine provides:

- **Python-based patterns** for maximum flexibility
- **Light grouping** (zones like left/right, front/back) AND independent per-light control
- **Scene system** for easy manual switching during sets
- **Hot-reload** for live pattern editing
- **Beat-synchronized phasers** (LFOs) instead of raw audio reactivity

## Component Documentation

| Document | Description |
|----------|-------------|
| [Pattern Engine](./pattern-engine.md) | Core engine design, PatternDef format, rendering pipeline |
| [Light Groups](./groups.md) | LightGroup, LightSetup, ZoneType definitions |
| [Scene System](./scenes.md) | Scenes, SceneBank, transitions, manual control |
| [Hot-Reload](./hot-reload.md) | File watching, pattern loading, live updates |
| [Future Ideas](./future-ideas.md) | Build/drop detection, GUI, auto-pilot, Serato integration |

## Current Architecture

### MIDI Clock Mode (`dj-hue`) - Recommended
```
Ableton MIDI Clock → Virtual Port → BeatClock → Phasers → RGB Colors → Hue Streaming
    (24 ticks/beat)                     ↑            ↓
                                   PatternDef    Render Thread
                                  (group effects)   (50 Hz)
                                        ↑
                                    Scene
                                 (modifiers)
```

The MIDI clock mode provides accurate beat sync by receiving timing directly from Ableton or similar DAWs.

## Key Files

| File | Purpose |
|------|---------|
| `src/dj_hue/lights/effects.py` | Core primitives: Phaser, BeatClock, RGB, waveforms |
| `src/dj_hue/patterns/` | Pattern engine module |
| `src/dj_hue/midi_pattern_mode.py` | MIDI clock integration with PatternEngine |
| `src/dj_hue/midi_hue.py` | Original MIDI clock mode (without PatternEngine) |
| `patterns/` | User pattern files (hot-reloaded) |
| `config.yaml` | Configuration including light setup |

## Implementation Status

- [x] Core beat clock and phaser system (effects.py)
- [x] Hue Entertainment API streaming
- [x] FFT beat detection
- [x] Pattern engine with groups (`src/dj_hue/patterns/engine.py`)
- [x] Light grouping system (`src/dj_hue/patterns/groups.py`)
- [x] Pattern definitions (`src/dj_hue/patterns/pattern_def.py`)
- [x] Scene system (`src/dj_hue/patterns/scenes.py`)
- [x] Hot-reload with watchdog (`src/dj_hue/patterns/loader.py`)
- [x] Built-in patterns (sine_wave, chase, pulse, strobe, left_right)
- [x] Example user patterns (`patterns/`)
- [x] MIDI clock integration (`midi_pattern_mode.py`)
- [x] Original MIDI mode (`midi_hue.py`)
- [ ] GUI (future phase)

## Entry Points

| Command | Description |
|---------|-------------|
| `dj-hue` | **Recommended** - MIDI clock mode with PatternEngine |
| `dj-hue-midi` | Original MIDI clock mode (without PatternEngine) |
| `python -m dj_hue` | Same as `dj-hue` |

## Keyboard Controls (Pattern Modes)

| Key | Action |
|-----|--------|
| `1-9` | Select scene |
| `[` / `]` | Previous / Next scene |
| `Space` | Toggle blackout |
| `f` | Flash (white) |
| `r` | Reset beat position |
| `h` | Show help |
| `q` | Quit |

## Quick Links

- [Example Pattern](./pattern-engine.md#example-pattern)
- [Creating a Light Setup](./groups.md#creating-a-setup)
- [Switching Scenes](./scenes.md#manual-switching)
