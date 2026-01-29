"""
Color palette system for deferred color resolution.

Palettes decouple color selection from pattern definition, allowing:
- Runtime palette switching without modifying patterns
- Selection modes: indexed, random, cycling, random-hold, random-blend
- Backwards-compatible with hardcoded colors

Usage:
    from dj_hue.patterns.strudel.palette import palette

    # In patterns
    light("all").color(palette(0))              # First color
    light("all").color(palette.random)          # Random per-event
    light("all").color(palette.cycle)           # Cycle through colors
    light("all").color(palette.random_hold(4))  # Random, changes every 4 beats
    light("all").color(palette.random_blend(4, 1))  # Random with 1-beat crossfade
"""

from dataclasses import dataclass
from enum import Enum, auto
from fractions import Fraction
from typing import TYPE_CHECKING, Sequence
import random

if TYPE_CHECKING:
    from .core.types import HSV

from .core.envelope import interpolate_hsv


class PaletteSelectionMode(Enum):
    """How to select colors from the palette."""

    INDEX = auto()  # Fixed index (modulo wrap)
    RANDOM = auto()  # Random per-event
    CYCLE = auto()  # Cycle sequentially through colors
    RANDOM_HOLD = auto()  # Random, held for N beats
    RANDOM_BLEND = auto()  # Random with crossfade transition
    CYCLE_HOLD = auto()  # Cycle through colors, held for N beats


@dataclass(frozen=True)
class PaletteRef:
    """
    A deferred reference to a palette color.

    This is NOT an HSV value - it's a description of HOW to pick a color
    from whatever palette is active at runtime.

    Examples:
        palette(0)              -> PaletteRef(mode=INDEX, index=0)
        palette.random          -> PaletteRef(mode=RANDOM)
        palette.cycle           -> PaletteRef(mode=CYCLE)
        palette.random_hold(4)  -> PaletteRef(mode=RANDOM_HOLD, hold_beats=4)
    """

    mode: PaletteSelectionMode
    index: int = 0  # For INDEX mode
    hold_beats: float = 1.0  # For RANDOM_HOLD mode
    blend_beats: float = 0.0  # For RANDOM_BLEND mode (fade duration)

    def resolve(
        self,
        palette: "Palette",
        event_index: int = 0,
        cycle_position: Fraction | None = None,
        seed: int | None = None,
    ) -> "HSV":
        """
        Resolve this reference to an actual HSV color.

        Args:
            palette: The active palette to select from
            event_index: Index of this event (for CYCLE mode)
            cycle_position: Current cycle position (for seeding RANDOM)
            seed: Optional seed for reproducible randomness
        """
        if self.mode == PaletteSelectionMode.INDEX:
            return palette[self.index]

        elif self.mode == PaletteSelectionMode.RANDOM:
            # Deterministic random based on event timing
            if seed is not None:
                rng = random.Random(seed)
            elif cycle_position is not None:
                # Use cycle position as seed for reproducibility within a cycle
                rng = random.Random(int(float(cycle_position) * 10000) + event_index)
            else:
                rng = random.Random()
            return rng.choice(palette.colors)

        elif self.mode == PaletteSelectionMode.CYCLE:
            return palette[event_index]

        elif self.mode == PaletteSelectionMode.RANDOM_HOLD:
            # Random but held for N beats, guaranteed different each time
            # Quantize cycle_position to hold_beats boundaries
            if cycle_position is not None:
                # cycle_position is in cycles (bars), convert to beats
                # 1 cycle = 4 beats
                pos_beats = float(cycle_position) * 4
                # Floor to nearest hold_beats boundary
                quantized = int(pos_beats / self.hold_beats)

                # Create a shuffled sequence of indices (deterministic per-session)
                # Using a fixed seed so the shuffle is consistent
                shuffle_rng = random.Random(42)
                indices = list(range(len(palette.colors)))
                shuffle_rng.shuffle(indices)

                # Cycle through the shuffled indices - guarantees no repeats
                # (except when wrapping, but that's unavoidable with small palettes)
                shuffled_index = indices[quantized % len(indices)]
                return palette[shuffled_index]
            elif seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            return rng.choice(palette.colors)

        elif self.mode == PaletteSelectionMode.CYCLE_HOLD:
            # Cycle through colors sequentially, held for N beats
            if cycle_position is not None:
                pos_beats = float(cycle_position) * 4
                quantized = int(pos_beats / self.hold_beats)
                return palette[quantized]
            return palette[event_index]

        elif self.mode == PaletteSelectionMode.RANDOM_BLEND:
            # Random with crossfade: hold for (period - fade), then blend to next
            if cycle_position is not None:
                pos_beats = float(cycle_position) * 4
                period = self.hold_beats
                fade = self.blend_beats

                # Which period are we in?
                period_index = int(pos_beats / period)
                pos_in_period = pos_beats % period

                # Create shuffled sequence (same logic as random_hold)
                shuffle_rng = random.Random(42)
                indices = list(range(len(palette.colors)))
                shuffle_rng.shuffle(indices)

                from_idx = indices[period_index % len(indices)]
                to_idx = indices[(period_index + 1) % len(indices)]

                # Are we in hold phase or fade phase?
                hold_duration = period - fade
                if pos_in_period < hold_duration or fade <= 0:
                    # Still holding (or no fade configured)
                    return palette[from_idx]
                else:
                    # Fading to next color
                    fade_progress = (pos_in_period - hold_duration) / fade
                    from_color = palette[from_idx]
                    to_color = palette[to_idx]
                    return interpolate_hsv(from_color, to_color, fade_progress)
            # Fallback for no cycle_position
            elif seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            return rng.choice(palette.colors)

        # Fallback
        return palette[0]


@dataclass(frozen=True)
class Palette:
    """
    A collection of colors that can be indexed, cycled, or randomly sampled.

    Palettes are immutable and can be shared across patterns.
    """

    name: str
    colors: tuple["HSV", ...]

    def __post_init__(self):
        if not self.colors:
            raise ValueError("Palette must have at least one color")

    def __len__(self) -> int:
        return len(self.colors)

    def __getitem__(self, index: int) -> "HSV":
        """Get color by index (wraps around)."""
        return self.colors[index % len(self.colors)]

    @classmethod
    def from_names(cls, name: str, color_names: Sequence[str]) -> "Palette":
        """Create palette from color name strings."""
        from .color import resolve_color

        colors = tuple(resolve_color(c) for c in color_names)
        return cls(name=name, colors=colors)

    @classmethod
    def from_hsv(cls, name: str, colors: Sequence["HSV"]) -> "Palette":
        """Create palette from HSV values."""
        return cls(name=name, colors=tuple(colors))


class PaletteAccessor:
    """
    Factory for creating PaletteRef instances.

    Usage:
        palette(0)              # Index 0
        palette(2)              # Index 2
        palette.random          # Random per-event
        palette.cycle           # Cycle through colors
        palette.random_hold(4)  # Random, changes every 4 beats
    """

    def __call__(self, index: int = 0) -> PaletteRef:
        """Create an indexed palette reference."""
        return PaletteRef(mode=PaletteSelectionMode.INDEX, index=index)

    @property
    def random(self) -> PaletteRef:
        """Create a random palette reference."""
        return PaletteRef(mode=PaletteSelectionMode.RANDOM)

    @property
    def cycle(self) -> PaletteRef:
        """Create a cycling palette reference."""
        return PaletteRef(mode=PaletteSelectionMode.CYCLE)

    def random_hold(self, beats: float = 1.0) -> PaletteRef:
        """
        Create a random palette reference that holds for N beats.

        Args:
            beats: How many beats to hold each random color (default 1.0)

        Examples:
            palette.random_hold(1)   # New random color every beat
            palette.random_hold(4)   # New random color every bar (4 beats)
            palette.random_hold(0.5) # New random color every half beat
        """
        return PaletteRef(mode=PaletteSelectionMode.RANDOM_HOLD, hold_beats=beats)

    def cycle_hold(self, beats: float = 4.0) -> PaletteRef:
        """
        Cycle through palette colors sequentially, holding each for N beats.

        Unlike random_hold, this cycles through colors in order (0, 1, 2, ...).
        Great for rainbow waves where you want the color to change each bar.

        Args:
            beats: How many beats to hold each color (default 4.0 = 1 bar)

        Examples:
            palette.cycle_hold(4)    # New color every bar (rainbow wave)
            palette.cycle_hold(1)    # New color every beat
            palette.cycle_hold(8)    # New color every 2 bars
        """
        return PaletteRef(mode=PaletteSelectionMode.CYCLE_HOLD, hold_beats=beats)

    def random_blend(self, period: float = 4.0, fade: float = 1.0) -> PaletteRef:
        """
        Create a random palette reference with crossfade transitions.

        Holds a random color, then crossfades to the next random color.

        Args:
            period: Total cycle length in beats (hold + fade)
            fade: Duration of the crossfade in beats

        Examples:
            palette.random_blend(4, 1)    # Hold 3 beats, fade 1 beat
            palette.random_blend(8, 2)    # Hold 6 beats, fade 2 beats
            palette.random_blend(4, 4)    # Continuous blend (always fading)
            palette.random_blend(4, 0)    # No fade (same as random_hold)
        """
        return PaletteRef(
            mode=PaletteSelectionMode.RANDOM_BLEND,
            hold_beats=period,
            blend_beats=min(fade, period),  # fade can't exceed period
        )


# Singleton instance for pattern authors
palette = PaletteAccessor()
