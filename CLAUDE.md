# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DJ-Hue is a beat-synchronized lighting control system for Philips Hue lights, designed for live DJ performances. It uses a Strudel-inspired functional pattern language to create composable, expressive lighting effects.

## Commands

```bash
# Install dependencies
uv sync

# Run main app (MIDI clock mode - recommended)
uv run dj-hue

# Alternative entry points
uv run dj-hue-midi   # Original MIDI mode without pattern engine
uv run dj-hue-link   # Ableton Link mode

# Development
uv run pytest        # Run tests (none currently exist)
uv run black src/    # Format code
uv run mypy src/     # Type check
```

## Architecture

### Core Data Flow
```
MIDI Clock (Ableton) → BeatClock → PatternEngine → RGB Colors → Hue Entertainment API
     24 ticks/beat                    ↑                              50 Hz streaming
                              Strudel Patterns
```

### Key Components

**Pattern Engine** (`src/dj_hue/patterns/engine.py`): Central rendering system that combines light groups, Strudel patterns, and beat clock to output RGB colors at 50Hz.

**Strudel DSL** (`src/dj_hue/patterns/strudel/`): Functional pattern language inspired by TidalCycles/Strudel. Patterns are query functions from time spans to light events.
- `dsl/constructors.py`: Entry points `light()`, `stack()`, `cat()`
- `core/pattern.py`: `LightPattern` class with chainable transforms
- `core/envelope.py`: ADSR envelope system for flash-and-fade
- `scheduler.py`: Converts patterns to RGB at query time

**Pattern Decorator** (`src/dj_hue/patterns/decorator.py`): Auto-discovery system. Patterns use `@pattern("Name", "description", tags=[...])` decorator for registration.

**Pattern Loader** (`src/dj_hue/patterns/loader.py`): Scans `patterns/` directory for `.py` files with `@pattern` decorators. Supports hot-reload via watchdog.

### Pattern Files Location

User patterns live in `/patterns/` (project root). Each file contains one or more `@pattern`-decorated functions returning `LightPattern`:

```python
from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, stack, cat, LightPattern

@pattern("My Pattern", "Description", tags=["flash"])
def my_pattern() -> LightPattern:
    return light("all").color("cyan")
```

### Strudel Pattern Basics

Patterns are built by chaining transformations:

```python
# Core constructors
light("all")              # Target lights via mini notation
stack(p1, p2)             # Layer patterns simultaneously
cat(p1, p2)               # Sequence patterns (each gets one cycle)

# Mini notation
"all"                     # All lights
"left right"              # Sequence left then right group
"0 1 2 3"                 # Sequence specific lights
"all ~"                   # On half, off half
"all ~*3"                 # On 1/4, rest 3/4 (downbeat)

# Transforms
.fast(2)                  # 2x speed
.slow(2)                  # Half speed
.seq()                    # Sequence through lights in group
.shuffle()                # Randomize order
.envelope(attack, fade, sustain)  # ADSR intensity
.color("cyan")            # Named color
.color(flash="white", fade="red")  # Flash then fade
.modulate("sine", frequency=1.0)   # LFO breathing
.zone("ceiling", fallback="all")   # Spatial targeting
```

## Configuration

- `config.yaml`: Hue bridge credentials and entertainment area ID
- `hue_credentials.json`: Bridge authentication (generated via setup)

## Documentation

See `docs/strudel-system.md` for comprehensive pattern system documentation including timing reference, all transforms, and examples.

## Maintenance

**Strudel Skill**: When making changes to the Strudel pattern system (new transforms, DSL changes, envelope parameters, etc.), update the skill at `~/.claude/skills/strudel-pattern/SKILL.md` to reflect those changes. This skill is used to create new patterns.
