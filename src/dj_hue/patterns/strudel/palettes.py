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
    # === Tonal palettes (shades of one color) ===
    "white_tones": ["#FFFFFF", "#FFE4C4", "#E0FFFF"],
    "red_tones": ["#FF0000", "#CC0000", "#FF4444", "#FF6B6B"],
    "orange_tones": ["#FF8000", "#FF6600", "#FFA500", "#FFAA33"],
    "blue_tones": ["#0066FF", "#0044CC", "#00BFFF", "#4169E1"],
    "purple_tones": ["#8B00FF", "#9400D3", "#BA55D3", "#DA70D6"],
    "green_tones": ["#00FF00", "#32CD32", "#00FA9A", "#7CFC00"],
    "pink_tones": ["#FF1493", "#FF69B4", "#FFB6C1", "#FF00FF"],
    # === Warm palettes ===
    "fire": ["#FF0000", "#FF4500", "#FF8C00", "#FFD700"],
    "sunset": ["#FF00FF", "#FF4500", "#9400D3", "#FF69B4"],
    "warm": ["#FF0000", "#FF8000", "#FFBF00", "#FFFF00"],
    "golden": ["#FFD700", "#FFA500", "#FF8C00", "#FF6347"],
    # === Cool palettes ===
    "ice": ["#00FFFF", "#0066FF", "#FFFFFF", "#E0FFFF"],
    "ocean": ["#0066FF", "#00FFFF", "#008080", "#00FF7F"],
    "cool": ["#0066FF", "#00FFFF", "#008080", "#8B00FF"],
    # === Vibrant/club palettes ===
    "neon": ["#FF1493", "#00FFFF", "#00FF00", "#8B00FF"],
    "club": ["#FF00FF", "#00FFFF", "#FFFFFF"],
    "rave": ["#FF1493", "#00FF00", "#00FFFF", "#8B00FF", "#FFFF00"],
    "synthwave": ["#FF00FF", "#00FFFF", "#FF006E", "#8338EC"],
    "vaporwave": ["#FF6B9D", "#C44569", "#6C5CE7", "#00CEC9"],
    "miami": ["#F72585", "#7209B7", "#3A0CA3", "#4CC9F0"],
    # === Full spectrum ===
    "rainbow": [
        "#FF0000",
        "#FF8000",
        "#FFFF00",
        "#00FF00",
        "#00FFFF",
        "#0000FF",
        "#8B00FF",
        "#FF00FF",
    ],
    # === Complementary pairs ===
    "red_cyan": ["#FF0000", "#00FFFF"],
    "orange_blue": ["#FF8000", "#0066FF"],
    "purple_lime": ["#8B00FF", "#00FF00"],
    "pink_teal": ["#FF1493", "#008080"],
    # === Flash palettes (white + color) ===
    "flash_red": ["#FFFFFF", "#FF0000"],
    "flash_cyan": ["#FFFFFF", "#00FFFF"],
    "flash_orange": ["#FFFFFF", "#FF8000"],
    "flash_blue": ["#FFFFFF", "#0066FF"],
    "flash_purple": ["#FFFFFF", "#8B00FF"],
    "flash_pink": ["#FFFFFF", "#FF1493"],
    "forest_adventure": ["#E7FF53", "#98FB50", "#8BFB8F", "#61CDFB", "#3982F5"],
    "fairfax": ["#67DFFA", "#92D6FB", "#F09896", "#EC5D57", "#E93330"],
    "warm_embrace": ["#ED7165", "#ED7159", "#EE8254", "#F0935A", "#F2A85F"],
    "ruby_glow": ["#F6C5CB", "#F2ACB6", "#F094A3", "#ED7E91", "#EB657E"],
}

# Register all built-in palettes on module import
for name, colors in _BUILTINS.items():
    register_palette(Palette.from_names(name, colors))
