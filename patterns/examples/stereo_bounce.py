"""
Stereo Bounce Pattern

Left and right sides alternate with complementary colors.
Creates a ping-pong effect synced to the beat.
"""

from dj_hue.patterns import Pattern, GroupEffect, Phaser, ColorPalette, HSV

pattern = Pattern(
    name="Stereo Bounce",
    description="Left/right alternating bounce",
    tags=["stereo", "bounce", "energy"],

    default_palette=ColorPalette(
        name="red_cyan",
        colors=[
            HSV(0.0, 1.0, 1.0),   # Red (color_index=0)
            HSV(0.55, 1.0, 1.0),  # Cyan (color_index=1)
        ]
    ),

    group_effects=[
        # Left side - red tones
        GroupEffect(
            group_name="left",
            intensity_phaser=Phaser(
                waveform="smooth_pulse",
                beats_per_cycle=1.0,
                phase_offset=0.0,
                min_value=0.1,
                max_value=1.0,
            ),
            color_index=0,  # Red
        ),
        # Right side - cyan, offset by half a beat
        GroupEffect(
            group_name="right",
            intensity_phaser=Phaser(
                waveform="smooth_pulse",
                beats_per_cycle=1.0,
                phase_offset=0.5,  # Half beat offset
                min_value=0.1,
                max_value=1.0,
            ),
            color_index=1,  # Cyan
        ),
    ],
)
