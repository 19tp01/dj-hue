"""
Spatial patterns for ceiling + perimeter setups.

These patterns leverage the dual-zone system for spatial effects using
the .zone() transform for composable zone targeting.

If a zone is missing, the pattern gracefully returns no events for that zone
(the .zone() transform returns [] when target zone doesn't exist).
"""

from ..strudel.dsl.constructors import light, stack, cat, ceiling, perimeter
from ..strudel.core.pattern import LightPattern


def get_spatial_presets() -> dict[str, tuple[LightPattern, str]]:
    """
    Get all spatial pattern presets.

    Returns:
        Dict mapping pattern name to (LightPattern, description) tuples.
    """
    return {
        # Spatial patterns (enhanced by ceiling)
        "sp_lightning": (lightning(), "Lightning strikes from ceiling, illuminates room"),
        "sp_heartbeat": (heartbeat(), "Double-pulse heartbeat, ceiling leads"),
        "sp_ripple": (ripple(), "Ripple from ceiling center to perimeter"),
        "sp_fire": (fire(), "Flames at perimeter, ember glow on ceiling"),
        "sp_comet": (comet(), "Comet enters from ceiling, trails around room"),
        "sp_sunrise": (sunrise(), "Slow sunrise: ceiling leads color transition"),
        "sp_aurora": (aurora(), "Aurora on ceiling, subtle reflection below"),
        # Structural patterns (require both zones)
        "sp_bullseye": (bullseye(), "Alternating rings: ceiling and perimeter"),
        "sp_vortex": (vortex(), "Spinning perimeter, calm ceiling eye"),
        "sp_portal": (portal(), "Portal on ceiling, energy emanates to perimeter"),
        # Complementary patterns (different behavior per zone)
        "sp_police": (police(), "Police lights: ceiling red, perimeter blue"),
        "sp_rainbow_breathe": (rainbow_breathe(), "Rainbow breathing with complementary colors per zone"),
    }


# =============================================================================
# SPATIAL PATTERNS (Enhanced by ceiling)
# =============================================================================


def lightning() -> LightPattern:
    """
    Lightning strikes from ceiling, illuminates room.

    Ceiling flashes first (the "sky"), perimeter follows 80ms later
    as the room is illuminated. Triggers on beat 1.
    """
    # Flash on beat 1, rest of bar silent (~*3 = 3 rests for beats 2,3,4)
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
        .late(0.02)  # ~80ms at 120bpm
        .zone("perimeter")
    )

    return stack(ceiling_flash, perimeter_flash)


def heartbeat() -> LightPattern:
    """
    Double-pulse heartbeat with ceiling as the heart.

    Ceiling beats at full intensity, perimeter echoes softer and delayed.
    Lub-dub pattern: beat on 1, beat on 2, rest on 3-4.
    """
    # Double-pulse pattern: lub (beat 1), dub (beat 2), rest (beats 3-4)
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
        .late(0.0125)  # ~50ms echo
        .zone("perimeter")
    )

    return stack(ceiling_beat, perimeter_beat)


def ripple() -> LightPattern:
    """
    Ripple emanates from ceiling center to perimeter.

    Like a pebble dropped in water - ceiling is the epicenter,
    perimeter receives the expanding wave.
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
        .late(0.05)  # Wave travel time
        .zone("perimeter")
    )

    return stack(ceiling_ripple, perimeter_ripple)


def fire() -> LightPattern:
    """
    Fire effect with ceiling as ember reflection.

    Perimeter has active flames (fast flickering), ceiling gets the
    softer reflected glow as light would bounce off a ceiling.
    """
    # Simulate flickering with fast random pops
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


def comet() -> LightPattern:
    """
    Comet enters from ceiling, trails around perimeter.

    Ceiling flash marks entry, then chase runs around perimeter.
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
        .late(0.0625)  # Trail starts after entry
        .zone("perimeter", fallback="all")
    )

    return stack(entry_flash, trail)


def sunrise() -> LightPattern:
    """
    Slow sunrise: ceiling (sky) leads color transition.

    Very slow color temperature shift from warm to cool,
    with ceiling leading and perimeter following.
    """
    # Warm to cool transition over 8 bars
    sky_transition = cat(
        light("all").color("red").envelope(attack=0.5, fade=0.5, sustain=0.8),
        light("all").color("orange").envelope(attack=0.5, fade=0.5, sustain=0.8),
        light("all").color("yellow").envelope(attack=0.5, fade=0.5, sustain=0.8),
        light("all").color("white").envelope(attack=0.5, fade=0.5, sustain=0.8),
    ).slow(2).zone("ceiling", fallback="all")  # 8 bars total

    room_transition = cat(
        light("all").color("red").envelope(attack=0.5, fade=0.5, sustain=0.6),
        light("all").color("orange").envelope(attack=0.5, fade=0.5, sustain=0.6),
        light("all").color("yellow").envelope(attack=0.5, fade=0.5, sustain=0.6),
        light("all").color("white").envelope(attack=0.5, fade=0.5, sustain=0.6),
    ).slow(2).late(0.5).zone("perimeter")  # Room follows sky

    return stack(sky_transition, room_transition)


def aurora() -> LightPattern:
    """
    Aurora borealis: full effect on ceiling, subtle reflection on perimeter.

    Ceiling shows flowing aurora colors, perimeter has muted ambient glow.
    """
    aurora_colors = cat(
        light("all").color("green").envelope(attack=0.4, fade=0.6, sustain=0.5),
        light("all").color("cyan").envelope(attack=0.4, fade=0.6, sustain=0.5),
        light("all").color("blue").envelope(attack=0.4, fade=0.6, sustain=0.5),
        light("all").color("purple").envelope(attack=0.4, fade=0.6, sustain=0.5),
    ).slow(2).zone("ceiling", fallback="all")  # 8 bar cycle

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


def bullseye() -> LightPattern:
    """
    Alternating rings: ceiling and perimeter alternate.

    Creates a pulsing target/bullseye effect using the natural ring structure.
    Falls back to even/odd alternation if zones missing.
    """
    ceiling_ring = light("all ~").color("red").zone("ceiling")
    perimeter_ring = light("~ all").color("blue").zone("perimeter")

    # Fallback for single zone - use even/odd
    even_ring = light("even ~").color("red")
    odd_ring = light("~ odd").color("blue")

    # Stack both approaches - zone ones will return [] if zones missing
    return stack(
        ceiling_ring,
        perimeter_ring,
        # Fallback patterns only active when no zones
        even_ring.zone("all"),  # Only if no ceiling/perimeter
        odd_ring.zone("all"),
    )


def vortex() -> LightPattern:
    """
    Vortex: perimeter spins, ceiling is calm eye of storm.

    Fast chase around perimeter while ceiling pulses slowly as the calm center.
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


def portal() -> LightPattern:
    """
    Portal: ceiling glows as portal, perimeter reacts with energy.

    Ceiling pulses intensely as a "portal opening", perimeter
    sparkles with emanating energy.
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


def police() -> LightPattern:
    """
    Police lights: ceiling is red, perimeter is blue, alternating.

    Uses the zone separation for the classic red/blue split.
    Falls back to left/right split if single zone.
    """
    ceiling_red = light("all ~").fast(4).color("red").zone("ceiling")
    perimeter_blue = light("~ all").fast(4).color("blue").zone("perimeter")

    # Fallback for single zone
    left_red = light("left ~").fast(4).color("red")
    right_blue = light("~ right").fast(4).color("blue")

    return stack(
        ceiling_red,
        perimeter_blue,
        # Fallback only active when zones missing
        left_red.zone("all"),
        right_blue.zone("all"),
    )


def rainbow_breathe() -> LightPattern:
    """
    Rainbow breathing with complementary colors per zone.

    Both zones breathe together, but ceiling and perimeter
    are offset by 180 degrees in hue for constant color contrast.
    """
    # These colors are roughly complementary
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
