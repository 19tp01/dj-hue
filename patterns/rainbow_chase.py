"""
Rainbow Chase Pattern

Fast chase pattern with rainbow colors spread across lights.
Great for high-energy moments.
"""

from dj_hue.patterns import pattern, light


@pattern("Rainbow Chase User", "Fast rainbow chase across all lights", tags=["rainbow", "chase", "energy"])
def rainbow_chase():
    """Rainbow chase with fast intensity cycling through colors."""
    from dj_hue.patterns import cat

    return (
        cat(
            light("all").seq().color("red"),
            light("all").seq().color("orange"),
            light("all").seq().color("yellow"),
            light("all").seq().color("green"),
            light("all").seq().color("cyan"),
            light("all").seq().color("blue"),
            light("all").seq().color("purple"),
            light("all").seq().color("magenta"),
        )
        .fast(8)  # Fast color cycling
        .modulate(
            wave="saw",
            frequency=1.0,  # One cycle per beat
            min_intensity=0.1,
            max_intensity=1.0,
        )
    )
