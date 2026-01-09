"""
Color palette system for deferred color resolution.

Palettes decouple color selection from pattern definition, allowing:
- Runtime palette switching without modifying patterns
- Selection modes: indexed, random, cycling
- Backwards-compatible with hardcoded colors

Usage:
    from dj_hue.patterns.strudel.palette import palette

    # In patterns
    light("all").color(palette(0))       # First color
    light("all").color(palette.random)   # Random per-event
    light("all").color(palette.cycle)    # Cycle through colors
"""

from dataclasses import dataclass
from enum import Enum, auto
from fractions import Fraction
from typing import TYPE_CHECKING, Sequence
import random

if TYPE_CHECKING:
    from .core.types import HSV


class PaletteSelectionMode(Enum):
    """How to select colors from the palette."""

    INDEX = auto()  # Fixed index (modulo wrap)
    RANDOM = auto()  # Random per-event
    CYCLE = auto()  # Cycle sequentially through colors


@dataclass(frozen=True)
class PaletteRef:
    """
    A deferred reference to a palette color.

    This is NOT an HSV value - it's a description of HOW to pick a color
    from whatever palette is active at runtime.

    Examples:
        palette(0)       -> PaletteRef(mode=INDEX, index=0)
        palette.random   -> PaletteRef(mode=RANDOM)
        palette.cycle    -> PaletteRef(mode=CYCLE)
    """

    mode: PaletteSelectionMode
    index: int = 0  # For INDEX mode

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
        palette(0)       # Index 0
        palette(2)       # Index 2
        palette.random   # Random per-event
        palette.cycle    # Cycle through colors
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


# Singleton instance for pattern authors
palette = PaletteAccessor()
