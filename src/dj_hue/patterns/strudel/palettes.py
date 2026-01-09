"""
Palette registry with built-in palettes.

Usage:
    from dj_hue.patterns.strudel.palettes import get_palette, PALETTES

    fire = get_palette("fire")
    print(PALETTES.keys())  # Available palette names
"""

from .palette import Palette

# Global palette registry
PALETTES: dict[str, Palette] = {}


def register_palette(palette: Palette) -> None:
    """Register a palette in the global registry."""
    PALETTES[palette.name] = palette


def get_palette(name: str) -> Palette | None:
    """Get a palette by name."""
    return PALETTES.get(name)


def list_palettes() -> list[str]:
    """Get list of all registered palette names."""
    return list(PALETTES.keys())


# Built-in palette definitions
# Can use named colors OR hex codes (copy/paste from palette websites)
_BUILTINS: dict[str, list[str]] = {
    # Warm palettes
    "fire": ["red", "orange", "yellow", "amber"],
    "sunset": ["magenta", "orange", "purple", "pink"],
    "warm": ["red", "orange", "amber", "yellow"],
    # Cool palettes
    "ice": ["cyan", "blue", "white", "cool_white"],
    "ocean": ["blue", "cyan", "teal", "green"],
    "cool": ["blue", "cyan", "teal", "violet"],
    # Vibrant/club palettes
    "neon": ["hot_pink", "cyan", "lime", "purple"],
    "club": ["magenta", "cyan", "white"],
    "rave": ["hot_pink", "lime", "cyan", "purple", "yellow"],
    # Full spectrum
    "rainbow": ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta"],
    # Monochrome
    "mono_white": ["white", "warm_white", "cool_white"],
    "mono_red": ["red", "dim_red", "orange"],
    "mono_blue": ["blue", "dim_blue", "cyan"],
    # Complementary pairs
    "red_cyan": ["red", "cyan"],
    "orange_blue": ["orange", "blue"],
    "purple_lime": ["purple", "lime"],
    # Accent palettes (primary + white flash)
    "flash_red": ["white", "red"],
    "flash_cyan": ["white", "cyan"],
    "flash_orange": ["white", "orange"],
    # Hex-based palettes (from popular color schemes)
    "synthwave": ["#FF00FF", "#00FFFF", "#FF006E", "#8338EC"],
    "vaporwave": ["#FF6B9D", "#C44569", "#6C5CE7", "#00CEC9"],
    "miami": ["#F72585", "#7209B7", "#3A0CA3", "#4CC9F0"],
    "golden": ["#FFD700", "#FFA500", "#FF8C00", "#FF6347"],
}

# Register all built-in palettes on module import
for name, colors in _BUILTINS.items():
    register_palette(Palette.from_names(name, colors))
