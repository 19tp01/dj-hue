"""Flash patterns - quick bursts and beat-synced flashes."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, LightPattern, palette


@pattern("Stagger", "Random sequential white flash, fades to palette", tags=["flash"], palette="fire")
def stagger_flash() -> LightPattern:
    """
    Random sequential white flash, each light fades to palette color.

    At the start of each bar, lights in a random sequence flash white
    successively in 16th notes at max brightness then dark, then fades
    up to 50% of the palette color until the next sequenced flash.
    """
    return (
        light("all")
        .seq(per_group=False)
        .shuffle()
        .envelope(attack=0.05, fade=1.0, sustain=0.5)
        .color(flash="white", fade=palette(0))
    )


@pattern("Beat Flash", "All lights flash on each beat", tags=["flash"], palette="ice")
def beat_flash() -> LightPattern:
    """All lights flash white on each beat (4 times per bar)."""
    return (
        light("all all all all")
        .envelope(attack=0.02, fade=0.2)
        .color(flash="white", fade=palette(0))
    )


@pattern("Downbeat", "Flash on beat 1 only", tags=["flash"], palette="fire")
def downbeat_flash() -> LightPattern:
    """Single flash on beat 1, fades for rest of bar."""
    return (
        light("all ~*3")
        .envelope(attack=0.02, fade=1.0, sustain=0.0)
        .color(flash="white", fade=palette(0))
    )
