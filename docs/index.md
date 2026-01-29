# DJ-Hue Pattern Engine Documentation

> **Purpose**: This documentation directory is for Claude Code to track ideas, TODOs, and implementation approaches for the dj-hue pattern engine system.

## Overview

DJ-Hue is a beat-synchronized lighting control system for Philips Hue lights, designed for live DJ performances. The pattern engine provides:

- **Strudel-inspired pattern language** - Composable, functional patterns for expressive lighting
- **Light grouping** (zones like left/right, front/back) AND independent per-light control
- **Mini notation** for quick pattern creation (`"all"`, `"left right"`, `"0 1 2 3"`)
- **ADSR envelopes** for flash-and-fade effects
- **Scene system** for easy manual switching during sets
- **Hot-reload** for live pattern editing

## Component Documentation

| Document | Description |
|----------|-------------|
| [Strudel System](./strudel-system.md) | Comprehensive pattern system docs: architecture, philosophy, original Strudel comparison |
| [Touch Controller](./touch-controller.md) | iPad/browser control: WebSocket protocol, architecture, low-latency USB setup |
| [Light Groups](./groups.md) | LightGroup, LightSetup, LightContext definitions |
| [Scene System](./scenes.md) | Scenes, SceneBank, transitions, manual control |
| [Hot-Reload](./hot-reload.md) | File watching, pattern loading, live updates |
| [Future Ideas](./future-ideas.md) | Build/drop detection, GUI, auto-pilot, Serato integration |

## Current Architecture

Two modes are available:

### MIDI Clock Mode (`dj-hue-midi-patterns`) - Recommended
```
Ableton MIDI Clock → Virtual Port → BeatClock → PatternEngine → RGB Colors → Hue Streaming
    (24 ticks/beat)                     ↑               ↓
                                   Strudel         Render Thread
                                   Patterns           (50 Hz)
```

### Audio Mode (`dj-hue-patterns`)
```
Audio Input → Beat Detector → BeatClock → PatternEngine → RGB Colors → Hue Streaming
                                ↑
                           Strudel Patterns
```

The MIDI clock mode provides more accurate beat sync by receiving timing directly from Ableton.

## Quick Start: Strudel Patterns

The Strudel system is the recommended way to create patterns:

```python
from dj_hue.patterns.strudel import light, stack, cat

# Simple flash on every beat
beat_flash = light("all all all all").envelope(attack=0.02, fade=0.2).color("white")

# Chase that runs through all lights
chase = light("all").seq().envelope(attack=0.1, fade=0.3).color("cyan")

# Stagger flash: random sequence, white flash fading to red
stagger = (
    light("all")
    .seq()
    .shuffle()
    .envelope(attack=0.05, fade=1.0, sustain=0.5)
    .color(flash="white", fade="red")
)

# Strobe build: doubles speed every 2 bars
strobe_build = cat(
    light("all ~").fast(2),   # Quarter notes
    light("all ~").fast(4),   # 8th notes
    light("all ~").fast(8),   # 16th notes
    light("all ~").fast(16),  # 32nd notes
).slow(2).color("white")
```

## Key Files

| File | Purpose |
|------|---------|
| `src/dj_hue/patterns/strudel/` | Strudel pattern system |
| `src/dj_hue/patterns/strudel/constructors.py` | `light()`, `stack()`, `cat()` |
| `src/dj_hue/patterns/strudel/pattern.py` | `LightPattern` with chainable transforms |
| `src/dj_hue/patterns/strudel/presets.py` | Ready-to-use pattern presets |
| `src/dj_hue/patterns/strudel/envelope.py` | ADSR envelopes |
| `src/dj_hue/patterns/engine.py` | PatternEngine (renders patterns) |
| `src/dj_hue/patterns/groups.py` | Light grouping system |
| `src/dj_hue/lights/effects.py` | Core primitives: Phaser, BeatClock, RGB |
| `src/dj_hue/midi_pattern_mode.py` | MIDI clock integration |
| `patterns/` | User pattern files (hot-reloaded) |
| `config.yaml` | Configuration including light setup |

## Implementation Status

- [x] Core beat clock and phaser system (effects.py)
- [x] Hue Entertainment API streaming
- [x] FFT beat detection
- [x] Pattern engine with groups (`src/dj_hue/patterns/engine.py`)
- [x] Light grouping system (`src/dj_hue/patterns/groups.py`)
- [x] **Strudel pattern system** (`src/dj_hue/patterns/strudel/`)
  - [x] Mini notation parser (`"all"`, `"left right"`, `"0 1 2 3"`)
  - [x] Time transforms: `fast()`, `slow()`, `early()`, `late()`
  - [x] Structural transforms: `seq()`, `shuffle()`, `rev()`
  - [x] Combinators: `stack()`, `cat()`
  - [x] ADSR envelopes with flash/fade colors
  - [x] Named colors and color transforms
  - [x] Pre-built pattern presets
- [x] Classic pattern definitions (Pattern, GroupEffect, Phaser)
- [x] Hot-reload with watchdog (`src/dj_hue/patterns/loader.py`)
- [x] MIDI clock integration (`midi_pattern_mode.py`)
- [x] Audio-based mode (`pattern_mode.py`)
- [x] **Touch controller** (`src/dj_hue/control/`, `src/dj_hue/touch/`, `touch-ui/`)
  - [x] WebSocket control server (pattern/palette selection, transport, quick actions)
  - [x] Touch server with WebSocket proxy
  - [x] React + Tailwind v4 touch-optimized UI
  - [x] Low-latency USB support via pymobiledevice3
- [ ] GUI (future phase)

## Entry Points

| Command | Description |
|---------|-------------|
| `dj-hue` | **Recommended** - MIDI clock mode with PatternEngine |
| `dj-hue-touch` | Touch server for iPad/browser control (serves UI on :8080) |
| `dj-hue-midi` | Original MIDI clock mode (without PatternEngine) |
| `dj-hue-link` | Ableton Link mode |

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

- [Strudel Pattern Examples](./strudel-system.md#examples)
- [Mini Notation Reference](./strudel-system.md#mini-notation-reference)
- [Creating a Light Setup](./groups.md#creating-a-setup)
- [Pre-built Pattern Presets](./strudel-system.md#presets)
- [Architecture Philosophy](./strudel-system.md#architectural-philosophy)
- [Comparison with Original Strudel](./strudel-system.md#comparison-with-original-strudel)
