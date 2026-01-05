"""
Warm Pulse Pattern

A gentle, ambient pattern with warm orange tones. Good for intros and chill moments.
"""

from dj_hue.patterns import Pattern, GroupEffect, Phaser, ColorPalette, HSV

pattern = Pattern(
    name="Warm Pulse",
    description="Gentle pulsing in warm colors",
    tags=["chill", "warm", "ambient", "intro"],

    default_palette=ColorPalette(
        name="warm_orange",
        colors=[
            HSV(0.08, 0.9, 1.0),  # Orange
        ]
    ),

    group_effects=[
        GroupEffect(
            group_name="all",
            intensity_phaser=Phaser(
                waveform="sine",
                beats_per_cycle=2.0,
                min_value=0.3,
                max_value=1.0,
            ),
            color_index=0,  # Use palette color 0 (orange)
            phase_spread=True,  # Gentle wave across lights
        ),
    ],
)
