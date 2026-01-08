"""
Pattern definition classes for the pattern engine.

Pattern is the declarative format for defining lighting patterns.
It references light groups by name, making patterns portable across setups.
Colors are referenced by palette index, allowing runtime color overrides.
"""

from dataclasses import dataclass, field
from typing import NamedTuple

from ...lights.effects import Phaser, LightEffect


class HSV(NamedTuple):
    """HSV color (hue, saturation, value) - all values 0.0-1.0."""
    hue: float  # 0.0-1.0, wraps around (red=0, green=0.33, blue=0.67)
    saturation: float = 1.0  # 0.0=white, 1.0=full color
    value: float = 1.0  # 0.0=black, 1.0=full brightness (used as max intensity)


@dataclass
class ColorPalette:
    """
    A set of colors that patterns can reference by index.

    Colors wrap with modulo if index >= len(colors).
    """
    name: str
    colors: list[HSV] = field(default_factory=list)

    def get_color(self, index: int) -> HSV:
        """Get color by index, wraps with modulo if index >= len(colors)."""
        if not self.colors:
            return HSV(0.0, 0.0, 1.0)  # White fallback
        return self.colors[index % len(self.colors)]

    def __len__(self) -> int:
        return len(self.colors)

    @classmethod
    def red(cls) -> "ColorPalette":
        """Single red color palette."""
        return cls(name="red", colors=[HSV(0.0, 1.0, 1.0)])

    @classmethod
    def warm(cls) -> "ColorPalette":
        """Warm colors: red, orange, amber."""
        return cls(name="warm", colors=[
            HSV(0.0, 1.0, 1.0),   # Red
            HSV(0.05, 1.0, 1.0),  # Orange
            HSV(0.08, 0.9, 1.0),  # Amber
        ])

    @classmethod
    def cool(cls) -> "ColorPalette":
        """Cool colors: blue, cyan, purple."""
        return cls(name="cool", colors=[
            HSV(0.6, 1.0, 1.0),   # Blue
            HSV(0.5, 1.0, 1.0),   # Cyan
            HSV(0.75, 1.0, 1.0),  # Purple
        ])

    @classmethod
    def rainbow(cls) -> "ColorPalette":
        """Full rainbow spectrum."""
        return cls(name="rainbow", colors=[
            HSV(0.0, 1.0, 1.0),   # Red
            HSV(0.08, 1.0, 1.0),  # Orange
            HSV(0.16, 1.0, 1.0),  # Yellow
            HSV(0.33, 1.0, 1.0),  # Green
            HSV(0.5, 1.0, 1.0),   # Cyan
            HSV(0.6, 1.0, 1.0),   # Blue
            HSV(0.75, 1.0, 1.0),  # Purple
        ])

    @classmethod
    def white(cls) -> "ColorPalette":
        """Single white color palette."""
        return cls(name="white", colors=[HSV(0.0, 0.0, 1.0)])


@dataclass
class GroupEffect:
    """
    Effect applied to a light group.

    This is the primary building block for pattern definitions. Each GroupEffect
    specifies which group of lights to affect and how to animate them.
    """
    group_name: str  # References LightGroup by name (e.g., "all", "left", "right")

    # Intensity control (required)
    intensity_phaser: Phaser

    # Color reference - index into pattern's palette
    color_index: int = 0

    # Optional hue animation (modulates around palette color)
    hue_phaser: Phaser | None = None

    # Phase spread: if True, phase_offset is spread across group members
    # e.g., for a 3-light group with phase_spread=True:
    #   light 0 gets phase_offset + 0/3 = +0.0
    #   light 1 gets phase_offset + 1/3 = +0.33
    #   light 2 gets phase_offset + 2/3 = +0.67
    # This creates chase effects automatically
    phase_spread: bool = False


@dataclass
class Pattern:
    """
    A complete pattern definition.

    Patterns are defined declaratively and reference groups by name.
    The same pattern can work with different light setups - the setup
    defines which lights are in each group.

    Colors are referenced by palette index, allowing runtime overrides.

    Example:
        pattern = Pattern(
            name="Warm Pulse",
            description="Gentle pulsing in warm colors",
            default_palette=ColorPalette.warm(),
            group_effects=[
                GroupEffect(
                    group_name="all",
                    intensity_phaser=Phaser(waveform="sine", beats_per_cycle=2.0),
                    color_index=0,  # First color in palette
                ),
            ],
        )
    """
    name: str
    description: str = ""

    # Tags for organization
    tags: list[str] = field(default_factory=list)

    # Default color palette (can be overridden at runtime)
    default_palette: ColorPalette = field(default_factory=ColorPalette.red)

    # Effects for each group (can have multiple effects for different groups)
    group_effects: list[GroupEffect] = field(default_factory=list)

    # Optional: independent light effects that override group effects
    # Key is the light index
    independent_effects: dict[int, LightEffect] = field(default_factory=dict)

    def get_effect_for_light(
        self,
        light_index: int,
        group_lookup: dict[str, list[int]],
    ) -> tuple[GroupEffect | None, int]:
        """
        Find the GroupEffect that applies to a specific light.

        Args:
            light_index: The light index to look up
            group_lookup: Dict mapping group names to light indices

        Returns:
            Tuple of (GroupEffect or None, position within group)
        """
        for group_effect in self.group_effects:
            group_indices = group_lookup.get(group_effect.group_name, [])
            if light_index in group_indices:
                position = group_indices.index(light_index)
                return group_effect, position
        return None, 0

    @classmethod
    def create_simple(
        cls,
        name: str,
        waveform: str = "sine",
        beats_per_cycle: float = 2.0,
        color_index: int = 0,
        phase_spread: bool = False,
        palette: ColorPalette | None = None,
        tags: list[str] | None = None,
    ) -> "Pattern":
        """
        Create a simple pattern affecting all lights.

        This is a convenience method for common patterns.
        """
        return cls(
            name=name,
            description=f"Simple {waveform} pattern",
            tags=tags or [],
            default_palette=palette or ColorPalette.red(),
            group_effects=[
                GroupEffect(
                    group_name="all",
                    intensity_phaser=Phaser(
                        waveform=waveform,
                        beats_per_cycle=beats_per_cycle,
                        min_value=0.1,
                        max_value=1.0,
                    ),
                    color_index=color_index,
                    phase_spread=phase_spread,
                ),
            ],
        )

    @classmethod
    def create_left_right(
        cls,
        name: str,
        left_color_index: int = 0,
        right_color_index: int = 1,
        waveform: str = "sine",
        beats_per_cycle: float = 2.0,
        offset: float = 0.5,  # Phase offset between left and right
        palette: ColorPalette | None = None,
    ) -> "Pattern":
        """
        Create a pattern with different effects for left and right groups.
        """
        return cls(
            name=name,
            description="Left/right split pattern",
            tags=["stereo", "split"],
            default_palette=palette or ColorPalette(
                name="red_blue",
                colors=[HSV(0.0, 1.0, 1.0), HSV(0.6, 1.0, 1.0)]  # Red, Blue
            ),
            group_effects=[
                GroupEffect(
                    group_name="left",
                    intensity_phaser=Phaser(
                        waveform=waveform,
                        beats_per_cycle=beats_per_cycle,
                        phase_offset=0.0,
                        min_value=0.1,
                        max_value=1.0,
                    ),
                    color_index=left_color_index,
                ),
                GroupEffect(
                    group_name="right",
                    intensity_phaser=Phaser(
                        waveform=waveform,
                        beats_per_cycle=beats_per_cycle,
                        phase_offset=offset,
                        min_value=0.1,
                        max_value=1.0,
                    ),
                    color_index=right_color_index,
                ),
            ],
        )

    @classmethod
    def create_chase(
        cls,
        name: str,
        waveform: str = "sawtooth",
        beats_per_cycle: float = 2.0,
        color_index: int = 0,
        palette: ColorPalette | None = None,
    ) -> "Pattern":
        """
        Create a chase pattern where lights animate in sequence.

        Uses phase_spread to automatically offset phases across the group.
        """
        return cls(
            name=name,
            description=f"{waveform} chase pattern",
            tags=["chase", "movement"],
            default_palette=palette or ColorPalette.red(),
            group_effects=[
                GroupEffect(
                    group_name="all",
                    intensity_phaser=Phaser(
                        waveform=waveform,
                        beats_per_cycle=beats_per_cycle,
                        min_value=0.05,
                        max_value=1.0,
                    ),
                    color_index=color_index,
                    phase_spread=True,  # Key: spreads phase across group
                ),
            ],
        )

    @classmethod
    def create_strobe(
        cls,
        name: str = "Strobe",
        beats_per_flash: float = 0.25,  # 4 flashes per beat
        palette: ColorPalette | None = None,
    ) -> "Pattern":
        """Create a strobe pattern for high-energy moments."""
        return cls(
            name=name,
            description="Strobe effect",
            tags=["strobe", "intense", "drop"],
            default_palette=palette or ColorPalette.white(),  # White strobe
            group_effects=[
                GroupEffect(
                    group_name="all",
                    intensity_phaser=Phaser(
                        waveform="square",
                        beats_per_cycle=beats_per_flash,
                        min_value=0.0,
                        max_value=1.0,
                    ),
                    color_index=0,
                ),
            ],
        )

    @classmethod
    def create_pulse(
        cls,
        name: str = "Pulse",
        beats_per_cycle: float = 1.0,
        color_index: int = 0,
        palette: ColorPalette | None = None,
    ) -> "Pattern":
        """Create a unified pulse where all lights pulse together."""
        return cls(
            name=name,
            description="Beat-synced pulse",
            tags=["pulse", "unified"],
            default_palette=palette or ColorPalette.red(),
            group_effects=[
                GroupEffect(
                    group_name="all",
                    intensity_phaser=Phaser(
                        waveform="smooth_pulse",
                        beats_per_cycle=beats_per_cycle,
                        min_value=0.1,
                        max_value=1.0,
                    ),
                    color_index=color_index,
                ),
            ],
        )


# Backwards compatibility alias
PatternDef = Pattern
