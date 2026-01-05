"""
Professional lighting effects engine using beat-synchronized phasers.

Based on industry-standard techniques from grandMA, Avolites, and other
professional lighting consoles. Uses LFO-based oscillators synced to tempo
rather than reactive amplitude mapping.
"""

from dataclasses import dataclass, field
from typing import Callable
import colorsys
import math
import time


# =============================================================================
# WAVEFORM GENERATORS
# =============================================================================

def waveform_sine(phase: float) -> float:
    """Sine wave: smooth, organic oscillation. phase 0-1 -> value 0-1"""
    return (math.sin(phase * 2 * math.pi) + 1) / 2


def waveform_triangle(phase: float) -> float:
    """Triangle wave: linear back-and-forth. phase 0-1 -> value 0-1"""
    return 1 - abs(2 * phase - 1)


def waveform_sawtooth(phase: float) -> float:
    """Sawtooth wave: ramp up, instant drop. phase 0-1 -> value 0-1"""
    return phase


def waveform_sawtooth_reverse(phase: float) -> float:
    """Reverse sawtooth: instant rise, ramp down. phase 0-1 -> value 0-1"""
    return 1 - phase


def waveform_square(phase: float, duty: float = 0.5) -> float:
    """Square wave: on/off. phase 0-1 -> value 0 or 1"""
    return 1.0 if phase < duty else 0.0


def waveform_pulse(phase: float) -> float:
    """Short pulse at start of cycle. phase 0-1 -> value 0-1"""
    return 1.0 if phase < 0.1 else 0.0


def waveform_smooth_pulse(phase: float) -> float:
    """Exponential decay pulse. phase 0-1 -> value 0-1"""
    return math.exp(-phase * 5)


WAVEFORMS: dict[str, Callable[[float], float]] = {
    'sine': waveform_sine,
    'triangle': waveform_triangle,
    'sawtooth': waveform_sawtooth,
    'sawtooth_rev': waveform_sawtooth_reverse,
    'square': waveform_square,
    'pulse': waveform_pulse,
    'smooth_pulse': waveform_smooth_pulse,
}


# =============================================================================
# PHASER (LFO) CLASS
# =============================================================================

@dataclass
class Phaser:
    """
    A beat-synchronized oscillator (LFO) for lighting effects.

    This is the core building block of professional lighting effects.
    Instead of reacting to audio amplitude, it generates smooth, rhythmic
    patterns locked to the tempo.
    """
    waveform: str = 'sine'           # Waveform type
    beats_per_cycle: float = 1.0     # How many beats for one full cycle
    phase_offset: float = 0.0        # Starting phase offset (0.0-1.0)
    min_value: float = 0.0           # Minimum output value
    max_value: float = 1.0           # Maximum output value

    def get_value(self, beat_position: float) -> float:
        """
        Get current value based on beat position.

        Args:
            beat_position: Current position in beats (e.g., 4.75 = 3/4 through beat 5)

        Returns:
            Value between min_value and max_value
        """
        # Calculate phase within cycle (0.0 to 1.0)
        cycle_position = (beat_position / self.beats_per_cycle + self.phase_offset) % 1.0

        # Get waveform function
        wave_func = WAVEFORMS.get(self.waveform, waveform_sine)

        # Calculate raw value (0-1)
        raw_value = wave_func(cycle_position)

        # Scale to min/max range
        return self.min_value + raw_value * (self.max_value - self.min_value)


# =============================================================================
# BEAT CLOCK
# =============================================================================

class BeatClock:
    """
    Tracks continuous position within the beat grid.

    Instead of just detecting beats, this maintains a running position
    (like 4.75 = three-quarters through beat 5) that phasers use to
    stay synchronized.
    """

    def __init__(self, bpm: float = 120.0):
        self.bpm = bpm
        self.beat_position = 0.0
        self.last_update = time.time()
        self._beat_times: list[float] = []  # Recent beat timestamps for BPM calc

    def update(self, detected_beat: bool = False, detected_bpm: float = None) -> None:
        """
        Update beat position. Call this every frame.

        Args:
            detected_beat: True if a beat was just detected
            detected_bpm: BPM from beat detector (for syncing)
        """
        now = time.time()
        elapsed = now - self.last_update

        # Update BPM if provided - use directly since beat detector already smooths
        if detected_bpm is not None and detected_bpm > 0:
            # Take the detector's BPM directly (it's already smoothed via median)
            self.bpm = detected_bpm

        # Advance position based on BPM (free-running, no phase snapping)
        beats_elapsed = elapsed * (self.bpm / 60.0)
        self.beat_position += beats_elapsed

        # Track beat times for reference (but don't snap position)
        if detected_beat:
            self._beat_times.append(now)
            # Keep only recent beats
            self._beat_times = [t for t in self._beat_times if now - t < 5.0]

        self.last_update = now

    def get_bar_position(self, beats_per_bar: int = 4) -> float:
        """Get position within current bar (0.0 to beats_per_bar)."""
        return self.beat_position % beats_per_bar

    def get_phrase_position(self, beats_per_phrase: int = 16) -> float:
        """Get position within current phrase (0.0 to beats_per_phrase)."""
        return self.beat_position % beats_per_phrase

    def reset(self) -> None:
        """Reset beat position to 0."""
        self.beat_position = 0.0
        self.last_update = time.time()


# =============================================================================
# RGB COLOR UTILITIES
# =============================================================================

@dataclass
class RGB:
    """RGB color value."""
    r: int
    g: int
    b: int

    @classmethod
    def from_hsv(cls, h: float, s: float, v: float) -> "RGB":
        """Create RGB from HSV (all values 0.0-1.0)."""
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
        return cls(int(r * 255), int(g * 255), int(b * 255))

    @classmethod
    def black(cls) -> "RGB":
        return cls(0, 0, 0)

    @classmethod
    def white(cls) -> "RGB":
        return cls(255, 255, 255)

    def dim(self, factor: float) -> "RGB":
        """Dim the color by a factor (0.0-1.0)."""
        factor = max(0.0, min(1.0, factor))
        return RGB(int(self.r * factor), int(self.g * factor), int(self.b * factor))


# =============================================================================
# EFFECT PATTERNS
# =============================================================================

@dataclass
class LightEffect:
    """Configuration for a single light's effect."""
    intensity_phaser: Phaser           # Controls brightness
    hue_phaser: Phaser | None = None   # Optional: controls color hue
    base_hue: float = 0.0              # Base hue (0.0-1.0)
    saturation: float = 1.0            # Color saturation


@dataclass
class Pattern:
    """A complete lighting pattern with effects for multiple lights."""
    name: str
    description: str
    effects: list[LightEffect] = field(default_factory=list)

    @classmethod
    def create_chase(
        cls,
        name: str,
        num_lights: int,
        waveform: str = 'sawtooth',
        beats_per_cycle: float = 1.0,
        base_hues: list[float] | None = None,
    ) -> "Pattern":
        """
        Create a chase pattern where lights are offset in phase.

        Args:
            name: Pattern name
            num_lights: Number of lights
            waveform: Waveform type
            beats_per_cycle: Beats per full cycle
            base_hues: List of base hues (or None for rainbow)
        """
        if base_hues is None:
            # Rainbow spread
            base_hues = [i / num_lights for i in range(num_lights)]

        effects = []
        for i in range(num_lights):
            phase_offset = i / num_lights  # Spread evenly across cycle

            effects.append(LightEffect(
                intensity_phaser=Phaser(
                    waveform=waveform,
                    beats_per_cycle=beats_per_cycle,
                    phase_offset=phase_offset,
                    min_value=0.05,
                    max_value=1.0,
                ),
                base_hue=base_hues[i % len(base_hues)],
                saturation=1.0,
            ))

        return cls(name=name, description=f"{waveform} chase", effects=effects)

    @classmethod
    def create_pulse(
        cls,
        name: str,
        num_lights: int,
        beats_per_cycle: float = 1.0,
        base_hue: float = 0.0,
    ) -> "Pattern":
        """Create a pulse pattern where all lights pulse together."""
        effects = []
        for i in range(num_lights):
            effects.append(LightEffect(
                intensity_phaser=Phaser(
                    waveform='smooth_pulse',
                    beats_per_cycle=beats_per_cycle,
                    phase_offset=0.0,
                    min_value=0.1,
                    max_value=1.0,
                ),
                base_hue=base_hue + i * 0.05,  # Slight hue variation
                saturation=1.0,
            ))

        return cls(name=name, description="Unified pulse", effects=effects)

    @classmethod
    def create_wave(
        cls,
        name: str,
        num_lights: int,
        beats_per_cycle: float = 2.0,
    ) -> "Pattern":
        """Create a smooth sine wave across lights."""
        effects = []
        for i in range(num_lights):
            phase_offset = i / num_lights

            effects.append(LightEffect(
                intensity_phaser=Phaser(
                    waveform='sine',
                    beats_per_cycle=beats_per_cycle,
                    phase_offset=phase_offset,
                    min_value=0.1,
                    max_value=1.0,
                ),
                # Hue also oscillates
                hue_phaser=Phaser(
                    waveform='triangle',
                    beats_per_cycle=beats_per_cycle * 4,
                    phase_offset=phase_offset,
                    min_value=0.0,
                    max_value=0.3,  # Shift hue by up to 30%
                ),
                base_hue=i / num_lights,
                saturation=0.9,
            ))

        return cls(name=name, description="Smooth sine wave", effects=effects)

    @classmethod
    def create_strobe(
        cls,
        name: str,
        num_lights: int,
        beats_per_flash: float = 0.25,  # 4 flashes per beat
    ) -> "Pattern":
        """Create a strobe pattern for drops."""
        effects = []
        for i in range(num_lights):
            effects.append(LightEffect(
                intensity_phaser=Phaser(
                    waveform='square',
                    beats_per_cycle=beats_per_flash,
                    phase_offset=0.0,
                    min_value=0.0,
                    max_value=1.0,
                ),
                base_hue=0.0,  # White strobe
                saturation=0.0,  # Desaturated = white
            ))

        return cls(name=name, description="Strobe effect", effects=effects)

    @classmethod
    def create_build(
        cls,
        name: str,
        num_lights: int,
    ) -> "Pattern":
        """Create a build-up pattern with accelerating sawtooth."""
        effects = []
        for i in range(num_lights):
            # Each light has slightly offset phase for chase effect
            phase_offset = i / num_lights

            effects.append(LightEffect(
                intensity_phaser=Phaser(
                    waveform='sawtooth',
                    beats_per_cycle=1.0,  # Will be modified dynamically
                    phase_offset=phase_offset,
                    min_value=0.2,
                    max_value=1.0,
                ),
                base_hue=0.0,  # Red for energy
                saturation=1.0,
            ))

        return cls(name=name, description="Build-up pattern", effects=effects)


# Pre-defined patterns
def get_default_patterns(num_lights: int) -> dict[str, Pattern]:
    """Get dictionary of default patterns for N lights."""
    return {
        # Smooth sine wave is now the default - less jarring
        'sine_wave': Pattern.create_wave('Sine Wave', num_lights, beats_per_cycle=2.0),
        'slow_wave': Pattern.create_wave('Slow Wave', num_lights, beats_per_cycle=4.0),
        'triangle_chase': Pattern.create_chase(
            'Triangle Chase',
            num_lights,
            waveform='triangle',
            beats_per_cycle=2.0,  # Slower - one cycle per 2 beats
        ),
        'sawtooth_chase': Pattern.create_chase(
            'Sawtooth Chase',
            num_lights,
            waveform='sawtooth',
            beats_per_cycle=2.0,  # Slower - was 1.0
            base_hues=[0.0, 0.1, 0.6, 0.7, 0.3, 0.4][:num_lights],
        ),
        'pulse': Pattern.create_pulse('Beat Pulse', num_lights, beats_per_cycle=1.0),
        'fast_chase': Pattern.create_chase(
            'Fast Chase',
            num_lights,
            waveform='sawtooth',
            beats_per_cycle=1.0,  # One cycle per beat
        ),
        'strobe': Pattern.create_strobe('Strobe', num_lights, beats_per_flash=0.25),  # Slower strobe
    }


# =============================================================================
# EFFECTS ENGINE
# =============================================================================

class EffectsEngine:
    """
    Main effects engine that combines beat clock, patterns, and generates colors.
    """

    def __init__(self, num_lights: int = 6):
        self.num_lights = num_lights
        self.beat_clock = BeatClock(bpm=120.0)
        self.patterns = get_default_patterns(num_lights)
        self.current_pattern_name = 'sine_wave'  # Smooth default
        self._pattern_names = list(self.patterns.keys())

    @property
    def current_pattern(self) -> Pattern:
        return self.patterns.get(self.current_pattern_name, self.patterns['sine_wave'])

    def set_pattern(self, name: str) -> None:
        """Set current pattern by name."""
        if name in self.patterns:
            self.current_pattern_name = name

    def next_pattern(self) -> str:
        """Cycle to next pattern."""
        idx = self._pattern_names.index(self.current_pattern_name)
        idx = (idx + 1) % len(self._pattern_names)
        self.current_pattern_name = self._pattern_names[idx]
        return self.current_pattern_name

    def update(self, detected_beat: bool = False, detected_bpm: float = None) -> None:
        """Update beat clock. Call every frame."""
        self.beat_clock.update(detected_beat, detected_bpm)

    def compute_colors(self) -> dict[int, RGB]:
        """
        Compute colors for all lights based on current pattern and beat position.

        Returns:
            Dictionary mapping light index to RGB color
        """
        colors = {}
        pattern = self.current_pattern
        beat_pos = self.beat_clock.beat_position

        for i in range(self.num_lights):
            if i < len(pattern.effects):
                effect = pattern.effects[i]
            else:
                # Fallback for lights beyond pattern definition
                effect = pattern.effects[i % len(pattern.effects)]

            # Get intensity from phaser
            intensity = effect.intensity_phaser.get_value(beat_pos)

            # Get hue (base + optional phaser modulation)
            hue = effect.base_hue
            if effect.hue_phaser:
                hue_offset = effect.hue_phaser.get_value(beat_pos)
                hue = (hue + hue_offset) % 1.0

            # Create color
            colors[i] = RGB.from_hsv(hue, effect.saturation, intensity)

        return colors

    def compute_unified_color(self) -> RGB:
        """
        Compute a single color for all lights (reduces jitter on Hue API).

        Uses the first light's effect settings but applies to all lights.
        This is smoother because all lights update simultaneously with same data.
        """
        pattern = self.current_pattern
        beat_pos = self.beat_clock.beat_position

        # Use first light's effect
        if pattern.effects:
            effect = pattern.effects[0]
        else:
            return RGB.white()

        # Get intensity from phaser
        intensity = effect.intensity_phaser.get_value(beat_pos)

        # Get hue (base + optional phaser modulation)
        hue = effect.base_hue
        if effect.hue_phaser:
            hue_offset = effect.hue_phaser.get_value(beat_pos)
            hue = (hue + hue_offset) % 1.0

        return RGB.from_hsv(hue, effect.saturation, intensity)

    def get_bpm(self) -> float:
        """Get current BPM."""
        return self.beat_clock.bpm

    def get_beat_position(self) -> float:
        """Get current beat position."""
        return self.beat_clock.beat_position
