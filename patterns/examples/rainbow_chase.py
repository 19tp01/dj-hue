"""
Rainbow Chase Pattern

Fast chase pattern with rainbow colors spread across lights.
Great for high-energy moments.
"""

from dj_hue.patterns import Pattern, GroupEffect, Phaser, ColorPalette

pattern = Pattern(
    name="Rainbow Chase",
    description="Fast rainbow chase across all lights",
    tags=["rainbow", "chase", "energy", "peak"],

    # Use rainbow palette
    default_palette=ColorPalette.rainbow(),

    group_effects=[
        GroupEffect(
            group_name="all",
            intensity_phaser=Phaser(
                waveform="sawtooth",
                beats_per_cycle=1.0,  # One cycle per beat
                min_value=0.1,
                max_value=1.0,
            ),
            # Hue also cycles, creating moving rainbow
            hue_phaser=Phaser(
                waveform="sawtooth",
                beats_per_cycle=8.0,  # Full rainbow over 8 beats
                min_value=0.0,
                max_value=1.0,
            ),
            color_index=0,  # Starting color (hue_phaser will modulate)
            phase_spread=True,
        ),
    ],
)
