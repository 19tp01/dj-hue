"""
Modulator class for time-varying intensity oscillation.

Provides LFO-style modulation that can be applied to light patterns
for effects like brightness pulsing and breathing.
"""

from dataclasses import dataclass
from enum import Enum
import math


class WaveType(Enum):
    """Supported waveform types for modulation."""

    SINE = "sine"
    TRIANGLE = "triangle"
    SAW = "saw"
    SQUARE = "square"


@dataclass
class Modulator:
    """
    LFO-style intensity modulator for lighting patterns.

    Applies oscillating intensity modulation based on absolute time
    (bar position), independent of individual event timing.

    Attributes:
        wave: The waveform type (sine, triangle, saw, square)
        frequency: Oscillations per bar (1.0 = one full cycle per bar)
        min_intensity: Minimum intensity (0.0-1.0)
        max_intensity: Maximum intensity (0.0-1.0)
        phase: Phase offset in cycles (0.0-1.0, default 0.0)

    Example:
        # Gentle breathing: 80-100% over each bar
        Modulator(WaveType.SINE, frequency=1.0, min_intensity=0.8, max_intensity=1.0)

        # Fast pulse: 50-100% 4x per bar
        Modulator(WaveType.SQUARE, frequency=4.0, min_intensity=0.5, max_intensity=1.0)
    """

    wave: WaveType = WaveType.SINE
    frequency: float = 1.0
    min_intensity: float = 0.0
    max_intensity: float = 1.0
    phase: float = 0.0

    def get_intensity(self, cycle_position: float) -> float:
        """
        Get the modulation intensity at a given cycle position.

        Args:
            cycle_position: Position in cycles (e.g., 2.5 = halfway through bar 3)

        Returns:
            Intensity multiplier between min_intensity and max_intensity
        """
        # Calculate phase within the wave cycle
        # Apply frequency and phase offset
        t = (cycle_position * self.frequency + self.phase) % 1.0

        # Get normalized wave value (0.0 to 1.0)
        if self.wave == WaveType.SINE:
            # Sine wave: 0 at t=0, 1 at t=0.25, 0 at t=0.5, -1 at t=0.75
            # Map from [-1, 1] to [0, 1]
            wave_value = (math.sin(t * 2 * math.pi) + 1) / 2

        elif self.wave == WaveType.TRIANGLE:
            # Triangle: 0 at t=0, 1 at t=0.5, 0 at t=1
            if t < 0.5:
                wave_value = t * 2
            else:
                wave_value = 2 - t * 2

        elif self.wave == WaveType.SAW:
            # Sawtooth: 0 at t=0, 1 at t=1 (ramps up)
            wave_value = t

        elif self.wave == WaveType.SQUARE:
            # Square: 1 for first half, 0 for second half
            wave_value = 1.0 if t < 0.5 else 0.0

        else:
            wave_value = 1.0

        # Map wave value to intensity range
        return self.min_intensity + wave_value * (self.max_intensity - self.min_intensity)
