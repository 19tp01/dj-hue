"""
Warm Pulse Pattern

A gentle, ambient pattern with warm orange tones. Good for intros and chill moments.
"""

from dj_hue.patterns import pattern, light, palette


@pattern("Warm Pulse", "Gentle pulsing in warm colors", tags=["chill", "warm", "ambient"], palette="warm")
def warm_pulse():
    """Warm pulse with phase spread across lights using palette colors."""
    return (
        light("all")
        .seq()
        .modulate(
            wave="sine",
            frequency=0.5,  # 2 beats per cycle
            min_intensity=0.3,
            max_intensity=1.0,
        )
        .color(palette(0))
    )
