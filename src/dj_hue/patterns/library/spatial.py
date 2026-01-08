"""Spatial patterns - ceiling + perimeter zone effects."""

from ..decorator import pattern
from ..strudel import light, stack, cat, LightPattern


# =============================================================================
# SPATIAL PATTERNS (Enhanced by ceiling)
# =============================================================================


@pattern("sp_lightning", "Lightning strikes from ceiling, illuminates room", tags=["spatial"])
def lightning() -> LightPattern:
    """
    Lightning strikes from ceiling, illuminates room.

    Ceiling flashes first (the "sky"), perimeter follows 80ms later.
    """
    ceiling_flash = (
        light("all ~*3")
        .color("white")
        .envelope(attack=0.01, fade=0.25, sustain=0.0)
        .zone("ceiling", fallback="all")
    )

    perimeter_flash = (
        light("all ~*3")
        .color("white")
        .envelope(attack=0.01, fade=0.4, sustain=0.0)
        .late(0.02)
        .zone("perimeter")
    )

    return stack(ceiling_flash, perimeter_flash)


@pattern("sp_heartbeat", "Double-pulse heartbeat, ceiling leads", tags=["spatial"])
def heartbeat() -> LightPattern:
    """
    Double-pulse heartbeat with ceiling as the heart.

    Lub-dub pattern: beat on 1, beat on 2, rest on 3-4.
    """
    ceiling_beat = (
        light("all all ~*2")
        .envelope(attack=0.02, fade=0.2, sustain=0.0)
        .color("red")
        .zone("ceiling", fallback="all")
    )

    perimeter_beat = (
        light("all all ~*2")
        .envelope(attack=0.02, fade=0.25, sustain=0.0)
        .color("red")
        .intensity(0.7)
        .late(0.0125)
        .zone("perimeter")
    )

    return stack(ceiling_beat, perimeter_beat)


@pattern("sp_ripple", "Ripple from ceiling center to perimeter", tags=["spatial"])
def ripple() -> LightPattern:
    """
    Ripple emanates from ceiling center to perimeter.

    Like a pebble dropped in water.
    """
    ceiling_ripple = (
        light("all")
        .color("cyan")
        .envelope(attack=0.02, fade=0.3)
        .zone("ceiling", fallback="all")
    )

    perimeter_ripple = (
        light("all")
        .seq()
        .color("cyan")
        .envelope(attack=0.05, fade=0.4)
        .late(0.05)
        .zone("perimeter")
    )

    return stack(ceiling_ripple, perimeter_ripple)


@pattern("sp_fire", "Flames at perimeter, ember glow on ceiling", tags=["spatial"])
def fire() -> LightPattern:
    """
    Fire effect with ceiling as ember reflection.

    Perimeter has active flames, ceiling gets softer reflected glow.
    """
    flames = (
        light("all all all all")
        .seq()
        .shuffle()
        .fast(4)
        .envelope(attack=0.01, fade=0.1)
        .color(flash="yellow", fade="orange")
        .zone("perimeter", fallback="all")
    )

    embers = (
        light("all")
        .envelope(attack=0.3, fade=0.5, sustain=0.4)
        .slow(2)
        .color("orange")
        .zone("ceiling")
    )

    return stack(flames, embers)


@pattern("sp_comet", "Comet enters from ceiling, trails around room", tags=["spatial"])
def comet() -> LightPattern:
    """
    Comet enters from ceiling, trails around perimeter.
    """
    entry_flash = (
        light("all")
        .color("white")
        .envelope(attack=0.01, fade=0.2)
        .zone("ceiling")
    )

    trail = (
        light("all")
        .seq()
        .envelope(attack=0.02, fade=0.3, sustain=0.1)
        .color(flash="white", fade="cyan")
        .late(0.0625)
        .zone("perimeter", fallback="all")
    )

    return stack(entry_flash, trail)


@pattern("sp_sunrise", "Slow sunrise: ceiling leads color transition", tags=["spatial", "ambient"])
def sunrise() -> LightPattern:
    """
    Slow sunrise: ceiling (sky) leads color transition.

    8 bar warm to cool transition.
    """
    sky_transition = cat(
        light("all").color("red").envelope(attack=0.5, fade=0.5, sustain=0.8),
        light("all").color("orange").envelope(attack=0.5, fade=0.5, sustain=0.8),
        light("all").color("yellow").envelope(attack=0.5, fade=0.5, sustain=0.8),
        light("all").color("white").envelope(attack=0.5, fade=0.5, sustain=0.8),
    ).slow(2).zone("ceiling", fallback="all")

    room_transition = cat(
        light("all").color("red").envelope(attack=0.5, fade=0.5, sustain=0.6),
        light("all").color("orange").envelope(attack=0.5, fade=0.5, sustain=0.6),
        light("all").color("yellow").envelope(attack=0.5, fade=0.5, sustain=0.6),
        light("all").color("white").envelope(attack=0.5, fade=0.5, sustain=0.6),
    ).slow(2).late(0.5).zone("perimeter")

    return stack(sky_transition, room_transition)


@pattern("sp_aurora", "Aurora on ceiling, subtle reflection below", tags=["spatial", "ambient"])
def aurora() -> LightPattern:
    """
    Aurora borealis: full effect on ceiling, subtle reflection on perimeter.
    """
    aurora_colors = cat(
        light("all").color("green").envelope(attack=0.4, fade=0.6, sustain=0.5),
        light("all").color("cyan").envelope(attack=0.4, fade=0.6, sustain=0.5),
        light("all").color("blue").envelope(attack=0.4, fade=0.6, sustain=0.5),
        light("all").color("purple").envelope(attack=0.4, fade=0.6, sustain=0.5),
    ).slow(2).zone("ceiling", fallback="all")

    ambient_reflection = (
        light("all")
        .envelope(attack=0.5, fade=0.5, sustain=0.3)
        .color("cyan")
        .slow(4)
        .zone("perimeter")
    )

    return stack(aurora_colors, ambient_reflection)


# =============================================================================
# STRUCTURAL PATTERNS (Require both zones)
# =============================================================================


@pattern("sp_bullseye", "Alternating rings: ceiling and perimeter", tags=["spatial"])
def bullseye() -> LightPattern:
    """
    Alternating rings: ceiling and perimeter alternate.

    Falls back to even/odd alternation if zones missing.
    """
    ceiling_ring = light("all ~").color("red").zone("ceiling")
    perimeter_ring = light("~ all").color("blue").zone("perimeter")

    even_ring = light("even ~").color("red")
    odd_ring = light("~ odd").color("blue")

    return stack(
        ceiling_ring,
        perimeter_ring,
        even_ring.zone("all"),
        odd_ring.zone("all"),
    )


@pattern("sp_vortex", "Spinning perimeter, calm ceiling eye", tags=["spatial"])
def vortex() -> LightPattern:
    """
    Vortex: perimeter spins, ceiling is calm eye of storm.
    """
    spinning_edge = (
        light("all")
        .seq()
        .fast(4)
        .envelope(attack=0.02, fade=0.1)
        .color("cyan")
        .zone("perimeter", fallback="all")
    )

    calm_eye = (
        light("all")
        .envelope(attack=0.5, fade=0.5, sustain=0.3)
        .slow(2)
        .color("blue")
        .zone("ceiling")
    )

    return stack(spinning_edge, calm_eye)


@pattern("sp_portal", "Portal on ceiling, energy emanates to perimeter", tags=["spatial"])
def portal() -> LightPattern:
    """
    Portal: ceiling glows as portal, perimeter reacts with energy.
    """
    portal_glow = (
        light("all")
        .envelope(attack=0.1, fade=0.3, sustain=0.7)
        .color("purple")
        .zone("ceiling")
    )

    energy_sparks = (
        light("all all all all")
        .seq()
        .shuffle()
        .envelope(attack=0.01, fade=0.15)
        .color(flash="white", fade="purple")
        .zone("perimeter")
    )

    return stack(portal_glow, energy_sparks)


# =============================================================================
# COMPLEMENTARY PATTERNS (Different behavior per zone)
# =============================================================================


@pattern("sp_police", "Police lights: ceiling red, perimeter blue", tags=["spatial"])
def police() -> LightPattern:
    """
    Police lights: ceiling is red, perimeter is blue, alternating.

    Falls back to left/right split if single zone.
    """
    ceiling_red = light("all ~").fast(4).color("red").zone("ceiling")
    perimeter_blue = light("~ all").fast(4).color("blue").zone("perimeter")

    left_red = light("left ~").fast(4).color("red")
    right_blue = light("~ right").fast(4).color("blue")

    return stack(
        ceiling_red,
        perimeter_blue,
        left_red.zone("all"),
        right_blue.zone("all"),
    )


@pattern("sp_rainbow_breathe", "Rainbow breathing with complementary colors per zone", tags=["spatial", "rainbow"])
def spatial_rainbow_breathe() -> LightPattern:
    """
    Rainbow breathing with complementary colors per zone.

    Ceiling and perimeter are offset by 180 degrees in hue.
    """
    ceiling_colors = cat(
        light("all").color("red").envelope(attack=0.4, fade=0.4, sustain=0.5),
        light("all").color("yellow").envelope(attack=0.4, fade=0.4, sustain=0.5),
        light("all").color("blue").envelope(attack=0.4, fade=0.4, sustain=0.5),
        light("all").color("magenta").envelope(attack=0.4, fade=0.4, sustain=0.5),
    ).zone("ceiling", fallback="all")

    perimeter_colors = cat(
        light("all").color("cyan").envelope(attack=0.4, fade=0.4, sustain=0.5),
        light("all").color("purple").envelope(attack=0.4, fade=0.4, sustain=0.5),
        light("all").color("orange").envelope(attack=0.4, fade=0.4, sustain=0.5),
        light("all").color("green").envelope(attack=0.4, fade=0.4, sustain=0.5),
    ).zone("perimeter")

    return stack(ceiling_colors, perimeter_colors)
