"""
Stereo Bounce Pattern

Left and right sides alternate with complementary colors.
Creates a ping-pong effect synced to the beat.
"""

from dj_hue.patterns import pattern, light, stack


@pattern("stereo_bounce", "Left/right alternating bounce", tags=["stereo", "bounce", "energy"])
def stereo_bounce():
    """Left and right groups alternate with red and cyan."""
    return stack(
        light("left")
        .modulate(
            wave="sine",
            frequency=1.0,  # 1 beat per cycle
            min_intensity=0.1,
            max_intensity=1.0,
            phase=0.0,
        )
        .color("red"),
        light("right")
        .modulate(
            wave="sine",
            frequency=1.0,
            min_intensity=0.1,
            max_intensity=1.0,
            phase=0.5,  # Half beat offset
        )
        .color("cyan"),
    )
