"""Pulse patterns - rhythmic intensity modulation."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, LightPattern, palette


@pattern(
    "Triangle Pulse",
    "Triangle wave pulse on every beat",
    tags=["pulse"],
    palette="neon",
)
def triangle_pulse() -> LightPattern:
    """Triangle wave from max to min brightness every beat."""
    return (
        light("all")
        .modulate("triangle", frequency=4.0, min_intensity=0.5, max_intensity=1.0)
        .color(palette.random_hold(4))  # New random color every bar
    )


@pattern(
    "Quarter Sawtooth Pulse",
    "Sawtooth decay from 100% to 80% every beat",
    tags=["pulse"],
    palette="neon",
)
def quarter_sawtooth_pulse() -> LightPattern:
    """Sawtooth wave: 100% at beat start, decays to 80% by end."""
    return (
        light("all")
        .modulate("saw", frequency=4.0, min_intensity=1.0, max_intensity=0.4)
        .color(palette.random_hold(8))  # New random color other every bar
    )


@pattern(
    "Half Bar Sawtooth Pulse",
    "Sawtooth decay from 100% to 50% every two beats",
    tags=["pulse"],
    palette="neon",
)
def half_bar_sawtooth_pulse() -> LightPattern:
    """Sawtooth wave: 100% at beat start, decays to 50% by end."""
    return (
        light("all")
        .modulate("saw", frequency=2.0, min_intensity=1.0, max_intensity=0.5)
        .color(palette.random_hold(8))  # New random color other every bar
    )


@pattern(
    "Layered Sawtooth",
    "Per-beat sawtooth with per-bar decay envelope",
    tags=["pulse"],
    palette="neon",
)
def layered_sawtooth() -> LightPattern:
    """
    Layered modulation: per-beat sawtooth × per-bar envelope.

    Each beat decays 100%→80%, and across the bar the overall
    intensity also decays, so beat 4 is dimmer than beat 1.
    """
    return (
        light("all")
        .modulate(
            "saw", frequency=4.0, min_intensity=1.0, max_intensity=0.8
        )  # per-beat
        .modulate(
            "saw", frequency=1.0, min_intensity=1.0, max_intensity=0.25
        )  # per-bar
        .color(palette.random_hold(4))  # New random color every bar
    )
