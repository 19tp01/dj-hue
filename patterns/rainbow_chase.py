"""
Rainbow Chase Pattern

Fast chase pattern with rainbow colors spread across lights.
Great for high-energy moments.
"""

from dj_hue.patterns import pattern, light, cat, palette


@pattern("Rainbow Chase User", "Fast rainbow chase across all lights", tags=["rainbow", "chase", "energy"], palette="rainbow")
def rainbow_chase():
    """Rainbow chase with fast intensity cycling through colors."""
    return (
        cat(*[light("all").seq() for _ in range(8)])
        .color(palette.cycle)
        .fast(8)  # Fast color cycling
        .modulate(
            wave="saw",
            frequency=1.0,  # One cycle per beat
            min_intensity=0.1,
            max_intensity=1.0,
        )
    )
