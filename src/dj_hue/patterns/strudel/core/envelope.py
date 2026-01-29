"""
Envelope class for time-varying intensity and color.

Provides ADSR-style envelopes that can be applied to light events
for effects like flash-then-fade.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import HSV
    from ..palette import PaletteRef


@dataclass
class Envelope:
    """
    ADSR-style envelope for lighting events.

    The envelope defines how intensity varies over time:
    - Attack: Ramp from 0 to 1.0 (peak intensity)
    - Decay: Ramp from 1.0 down to sustain level
    - Sustain: Hold at sustain level
    - Release: Ramp from sustain to 0 (after event ends)

    For the "flash then fade" effect:
    - attack=0.05 (quick flash to peak)
    - decay=4.0 (slow fade over 4 cycles)
    - sustain=0.5 (end at 50% intensity)
    - flash_color=white, fade_color=red

    All time values are in cycles (1 cycle = 1 bar = 4 beats).
    """
    attack: float = 0.0
    decay: float = 0.0
    sustain: float = 1.0
    release: float = 0.0

    # Color transitions (literal HSV values)
    flash_color: "HSV | None" = None  # Color during attack phase
    fade_color: "HSV | None" = None   # Color during decay/sustain phase

    # Palette references (for deferred color resolution)
    flash_ref: "PaletteRef | None" = None  # Palette ref for attack phase
    fade_ref: "PaletteRef | None" = None   # Palette ref for decay/sustain

    @property
    def total_duration(self) -> float:
        """Total envelope duration (attack + decay), not including release."""
        return self.attack + self.decay

    def get_intensity(self, time_in_event: float) -> float:
        """
        Get intensity at a given time within the event.

        Args:
            time_in_event: Time in cycles since event started (0.0 = event start)

        Returns:
            Intensity multiplier (0.0-1.0)
        """
        if time_in_event < 0:
            return 0.0

        # Attack phase: ramp up to peak
        # At t=0, we're already at peak (instant flash), then quick ramp down and back up
        # This ensures the first frame is never black
        if time_in_event < self.attack:
            if self.attack <= 0:
                return 1.0
            # Use smoothstep curve that starts at 1.0, dips slightly, returns to 1.0
            # This gives a "punch" effect without the first-frame dropout
            t = time_in_event / self.attack
            # Start at 1.0, end at 1.0, with slight dip in middle for very short attacks
            # For longer attacks, this approaches a linear ramp
            return max(0.1, t) if self.attack > 0.05 else 1.0

        # Decay phase: ramp down from 1 to sustain
        time_after_attack = time_in_event - self.attack
        if time_after_attack < self.decay:
            if self.decay <= 0:
                return self.sustain
            t = time_after_attack / self.decay
            return 1.0 - t * (1.0 - self.sustain)

        # Sustain phase: hold at sustain level
        return self.sustain

    def get_release_intensity(self, time_since_release: float) -> float:
        """
        Get intensity during release phase (after event ends).

        Args:
            time_since_release: Time in cycles since release started

        Returns:
            Intensity multiplier (0.0 to sustain level)
        """
        if self.release <= 0:
            return 0.0
        if time_since_release >= self.release:
            return 0.0
        t = time_since_release / self.release
        return self.sustain * (1.0 - t)

    def get_color(self, time_in_event: float, base_color: "HSV") -> "HSV":
        """
        Get color at a given time, interpolating between flash and fade colors.

        Args:
            time_in_event: Time in cycles since event started
            base_color: Default color if no envelope colors specified

        Returns:
            HSV color for this time point
        """
        # During attack phase, use flash color if available
        if time_in_event < self.attack:
            if self.flash_color:
                return self.flash_color
            if self.fade_color:
                return self.fade_color
            return base_color

        # After attack, use fade color or interpolate
        if self.fade_color:
            if self.flash_color and self.decay > 0:
                # Interpolate from flash to fade during decay
                time_after_attack = time_in_event - self.attack
                if time_after_attack < self.decay:
                    t = time_after_attack / self.decay
                    return interpolate_hsv(self.flash_color, self.fade_color, t)
            return self.fade_color

        if self.flash_color:
            return self.flash_color

        return base_color

    def with_colors(
        self,
        flash: "HSV | None" = None,
        fade: "HSV | None" = None,
    ) -> "Envelope":
        """Return a new envelope with updated colors (clears refs for set colors)."""
        return Envelope(
            attack=self.attack,
            decay=self.decay,
            sustain=self.sustain,
            release=self.release,
            flash_color=flash if flash is not None else self.flash_color,
            fade_color=fade if fade is not None else self.fade_color,
            flash_ref=None if flash is not None else self.flash_ref,
            fade_ref=None if fade is not None else self.fade_ref,
        )

    def with_flash_ref(self, ref: "PaletteRef") -> "Envelope":
        """Return a new envelope with flash palette reference (clears flash_color)."""
        return Envelope(
            attack=self.attack,
            decay=self.decay,
            sustain=self.sustain,
            release=self.release,
            flash_color=None,
            fade_color=self.fade_color,
            flash_ref=ref,
            fade_ref=self.fade_ref,
        )

    def with_fade_ref(self, ref: "PaletteRef") -> "Envelope":
        """Return a new envelope with fade palette reference (clears fade_color)."""
        return Envelope(
            attack=self.attack,
            decay=self.decay,
            sustain=self.sustain,
            release=self.release,
            flash_color=self.flash_color,
            fade_color=None,
            flash_ref=self.flash_ref,
            fade_ref=ref,
        )

    def merge(self, other: "Envelope | None") -> "Envelope":
        """
        Merge with another envelope, preferring self's non-default values.
        """
        if other is None:
            return self
        return Envelope(
            attack=self.attack if self.attack != 0 else other.attack,
            decay=self.decay if self.decay != 0 else other.decay,
            sustain=self.sustain if self.sustain != 1.0 else other.sustain,
            release=self.release if self.release != 0 else other.release,
            flash_color=self.flash_color or other.flash_color,
            fade_color=self.fade_color or other.fade_color,
            flash_ref=self.flash_ref or other.flash_ref,
            fade_ref=self.fade_ref or other.fade_ref,
        )


def interpolate_hsv(c1: "HSV", c2: "HSV", t: float) -> "HSV":
    """
    Linearly interpolate between two HSV colors.

    Args:
        c1: Start color
        c2: End color
        t: Interpolation factor (0.0 = c1, 1.0 = c2)

    Returns:
        Interpolated HSV color
    """
    from .types import HSV

    t = max(0.0, min(1.0, t))

    # Handle hue wrapping (take shortest path around the color wheel)
    h1, h2 = c1.hue, c2.hue
    if abs(h2 - h1) > 0.5:
        if h1 < h2:
            h1 += 1.0
        else:
            h2 += 1.0

    hue = (h1 + (h2 - h1) * t) % 1.0
    sat = c1.saturation + (c2.saturation - c1.saturation) * t
    val = c1.value + (c2.value - c1.value) * t

    return HSV(hue, sat, val)
