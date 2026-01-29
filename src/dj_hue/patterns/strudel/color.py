"""
Color utilities for the Strudel pattern system.

Provides color name resolution and color manipulation functions.
"""

import colorsys

from .core.types import HSV


def hsv_to_hex(color: HSV) -> str:
    """
    Convert HSV color to hex string.

    Args:
        color: HSV color tuple

    Returns:
        Hex string like "#FF6B00"
    """
    r, g, b = colorsys.hsv_to_rgb(color.hue, color.saturation, color.value)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def hex_to_hsv(hex_color: str) -> HSV:
    """
    Convert hex color string to HSV.

    Args:
        hex_color: Hex string like "#FF6B00", "#F60", "FF6B00"

    Returns:
        HSV color tuple

    Raises:
        ValueError: If hex format is invalid
    """
    # Strip # prefix if present
    hex_str = hex_color.lstrip("#")

    # Expand shorthand (#RGB -> #RRGGBB)
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)

    if len(hex_str) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")

    try:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
    except ValueError:
        raise ValueError(f"Invalid hex color: {hex_color}")

    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return HSV(h, s, v)


# Named colors (hue, saturation, value)
NAMED_COLORS: dict[str, HSV] = {
    # Primary colors
    "red": HSV(0.0, 1.0, 1.0),
    "orange": HSV(0.08, 1.0, 1.0),
    "yellow": HSV(0.16, 1.0, 1.0),
    "green": HSV(0.33, 1.0, 1.0),
    "cyan": HSV(0.5, 1.0, 1.0),
    "blue": HSV(0.6, 1.0, 1.0),
    "purple": HSV(0.75, 1.0, 1.0),
    "magenta": HSV(0.83, 1.0, 1.0),
    "pink": HSV(0.9, 0.6, 1.0),

    # Whites and neutrals
    "white": HSV(0.0, 0.0, 1.0),
    "warm_white": HSV(0.08, 0.2, 1.0),
    "cool_white": HSV(0.55, 0.1, 1.0),

    # Dimmed variants
    "dim_red": HSV(0.0, 1.0, 0.5),
    "dim_blue": HSV(0.6, 1.0, 0.5),
    "dim_white": HSV(0.0, 0.0, 0.5),

    # DJ-friendly colors
    "amber": HSV(0.1, 1.0, 1.0),
    "lime": HSV(0.25, 1.0, 1.0),
    "teal": HSV(0.45, 1.0, 1.0),
    "violet": HSV(0.7, 1.0, 1.0),
    "hot_pink": HSV(0.92, 1.0, 1.0),
}


def color_from_name(name: str) -> HSV:
    """
    Resolve a color name to an HSV value.

    Args:
        name: Color name (e.g., "red", "white", "cyan")

    Returns:
        HSV color tuple

    Raises:
        ValueError: If color name is not recognized
    """
    name_lower = name.lower().strip()
    if name_lower in NAMED_COLORS:
        return NAMED_COLORS[name_lower]
    raise ValueError(f"Unknown color name: {name}")


def resolve_color(color: HSV | str | None) -> HSV | None:
    """
    Resolve a color that may be a name string, hex string, or HSV tuple.

    Args:
        color: Either an HSV tuple, a color name string, hex string (#RGB or #RRGGBB), or None

    Returns:
        HSV color or None
    """
    if color is None:
        return None
    if isinstance(color, str):
        # Detect hex colors
        if color.startswith("#"):
            return hex_to_hsv(color)
        return color_from_name(color)
    return color


def hue_rotate(color: HSV, amount: float) -> HSV:
    """
    Rotate the hue of a color.

    Args:
        color: Original HSV color
        amount: Amount to rotate (0.0-1.0, wraps around)

    Returns:
        New HSV with rotated hue
    """
    new_hue = (color.hue + amount) % 1.0
    return HSV(new_hue, color.saturation, color.value)


def dim(color: HSV, factor: float) -> HSV:
    """
    Dim a color by reducing its value.

    Args:
        color: Original HSV color
        factor: Dimming factor (0.0 = black, 1.0 = original)

    Returns:
        Dimmed HSV color
    """
    return HSV(color.hue, color.saturation, color.value * factor)


def saturate(color: HSV, factor: float) -> HSV:
    """
    Adjust saturation of a color.

    Args:
        color: Original HSV color
        factor: Saturation multiplier (0.0 = white, 1.0 = original, >1.0 = more saturated)

    Returns:
        HSV with adjusted saturation
    """
    new_sat = max(0.0, min(1.0, color.saturation * factor))
    return HSV(color.hue, new_sat, color.value)
