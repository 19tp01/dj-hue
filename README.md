<div align="center">
  <h1>DJ-Hue</h1>
  <p>Beat-synchronized Philips Hue lighting for live DJ performances</p>
</div>

## Screenshots

<img width="2452" height="1850" alt="CleanShot 2026-01-28 at 22 52 13@2x" src="https://github.com/user-attachments/assets/5a240b68-2c21-4430-af23-85bed6daba1a" />
<img width="2446" height="1840" alt="CleanShot 2026-01-28 at 22 46 36@2x" src="https://github.com/user-attachments/assets/c9b17190-3d51-4976-a5a9-8b805567a80f" />


## About

DJ-Hue syncs Philips Hue lights to music in real-time using MIDI clock from Ableton or other DAWs. I built this for my own DJ setup after finding existing solutions either too limited or not designed for live performance. The system uses a Strudel-inspired functional pattern language (borrowed from TidalCycles) which makes creating complex, beat-synced lighting effects surprisingly expressive and composable.

### Built With

* Python 3.10+ with asyncio
* Strudel-inspired functional DSL for pattern composition
* Philips Hue Entertainment API (50Hz streaming)
* React + TypeScript + Tailwind CSS (touch controller UI)
* MIDI Clock / Ableton Link for beat sync

## Getting Started

### Prerequisites

* Python 3.10-3.12
* [uv](https://github.com/astral-sh/uv) package manager
* Philips Hue Bridge with Entertainment API enabled
* Philips Hue lights configured in an Entertainment Area
* MIDI clock source (Ableton, Traktor, etc.)

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/yourusername/dj-hue.git
   cd dj-hue
   ```

2. Install dependencies
   ```sh
   uv sync
   ```

3. Copy the example config and edit with your settings
   ```sh
   cp config.example.yaml config.yaml
   ```

4. Run setup to generate Hue credentials (press the bridge button when prompted)
   ```sh
   uv run dj-hue --setup
   ```

5. Run the app
   ```sh
   uv run dj-hue
   ```

### Environment Variables

None required. All configuration lives in `config.yaml`.

### Touch Controller (Optional)

For iPad/browser control, run the touch server in a separate terminal:

```sh
uv run dj-hue-touch
```

Then open `http://<your-mac-ip>:8080` on your iPad.

## How It Works

```
MIDI Clock (Ableton) -> BeatClock -> PatternEngine -> Hue Entertainment API
     24 ticks/beat                      |                   50 Hz streaming
                                   Strudel Patterns
                                        |
                              Touch Controller (iPad)
```

**Pattern Language**: Patterns are defined as pure functions from time spans to lighting events. This functional approach (from TidalCycles/Strudel) enables patterns to be infinitely long, deterministic, and composable:

```python
# Simple pulse on the beat
light("all").color("white").envelope(attack=0.05, fade=0.3)

# Rainbow chase across all lights
light("all").seq().color("rainbow").fast(2)

# Layer multiple patterns
stack(
    light("left").color("cyan").modulate("sine"),
    light("right").color("magenta").modulate("sine").early(0.5)
)
```

Patterns live in `/patterns/` as `.pattern` files and hot-reload when modified.

**Timing Precision**: Uses Python's `Fraction` class for exact beat arithmetic, preventing drift over long sets.
