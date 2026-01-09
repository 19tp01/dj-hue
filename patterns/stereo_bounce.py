"""
Stereo Bounce Pattern

Left and right sides alternate with complementary colors.
Creates a ping-pong effect synced to the beat.
"""

from dj_hue.patterns import pattern, light, stack, palette


@pattern("Stereo Bounce", "Left/right alternating bounce", tags=["stereo", "bounce", "energy"], palette="red_cyan")
def stereo_bounce():
    """Left and right groups alternate with palette complementary colors."""
    return stack(
        light("left")
        .modulate(
            wave="sine",
            frequency=1.0,  # 1 beat per cycle
            min_intensity=0.1,
            max_intensity=1.0,
            phase=0.0,
        )
        .color(palette(0)),
        light("right")
        .modulate(
            wave="sine",
            frequency=1.0,
            min_intensity=0.1,
            max_intensity=1.0,
            phase=0.5,  # Half beat offset
        )
        .color(palette(1)),
    )
