"""Signature patterns - complex multi-layer effects."""

from dj_hue.patterns.decorator import pattern
from dj_hue.patterns.strudel import light, stack, cat, LightPattern


@pattern("Green Cascade", "Neon green with sequential white flash at bar start", tags=["signature"])
def green_cascade() -> LightPattern:
    """
    Neon green with alternating even/odd pulse and sequential flash at bar start.

    Base: Even lights pulse on quarter notes 1,3; odd lights on 2,4
    Flash: Sequential white flash through ALL lights on 16th notes
    """
    return stack(
        # Base layer: Even lights on quarter notes 1 and 3
        light("even ~ even ~")
        .envelope(attack=0.02, fade=0.2, sustain=0.8)
        .color("lime"),
        # Base layer: Odd lights on quarter notes 2 and 4
        light("~ odd ~ odd")
        .envelope(attack=0.02, fade=0.2, sustain=0.8)
        .color("lime"),
        # Flash layer: sequential white flash through ALL lights
        light("all")
        .seq(slots=16, per_group=False)
        .envelope(attack=0.01, fade=0.12)
        .color(flash="white", fade="lime"),
    )


@pattern("Blue Fade Strobe", "2 beats bright blue fade, 2 beats blue strobe", tags=["signature"])
def blue_fade_strobe() -> LightPattern:
    """
    2 beats bright blue fade to 50%, then 2 beats blue strobe.

    First half of bar (beats 1-2): Bright blue flash, fades to 50%
    Second half of bar (beats 3-4): Blue strobe at 16th note speed
    """
    return cat(
        light("all").envelope(attack=0.02, fade=0.95, sustain=0.2).color("blue"),
        light("all ~").fast(4).color("blue"),
    ).fast(2)


@pattern("Rainbow Chase", "Rainbow colors chase on half notes", tags=["signature", "rainbow"])
def rainbow_chase() -> LightPattern:
    """
    Rainbow colors chase through lights on half notes.

    Each half note, lights sequence through with a new color.
    Full rainbow cycle takes 4 bars.
    """
    return cat(
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("red"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("orange"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("yellow"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("green"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("cyan"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("blue"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("purple"),
        light("all").seq().envelope(attack=0.02, fade=0.4, sustain=0.0).color("magenta"),
    ).fast(2)


@pattern("Rainbow Breathe", "Rainbow breathing with sine wave 80-100%", tags=["signature", "rainbow"])
def rainbow_breathe() -> LightPattern:
    """
    Rainbow colors fading smoothly with brightness sine wave.

    Colors cycle through the full spectrum (8 colors per bar).
    Brightness oscillates from 80% to 100% every 4 bars.
    """
    return (
        cat(
            light("all").color("red"),
            light("all").color("orange"),
            light("all").color("yellow"),
            light("all").color("green"),
            light("all").color("cyan"),
            light("all").color("blue"),
            light("all").color("purple"),
            light("all").color("magenta"),
        )
        .fast(8)
        .modulate(
            wave="triangle",
            frequency=0.25,
            min_intensity=0.8,
            max_intensity=1.0,
            phase=0.25,
        )
    )
