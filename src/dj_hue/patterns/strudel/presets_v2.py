"""
Layered spatial patterns for ceiling + perimeter setups.

These patterns leverage the dual-zone system for spatial effects,
with graceful degradation to single-zone fallbacks.
"""

from .constructors import light, stack, cat, ceiling, perimeter
from .layered import LayeredPattern
from ..metadata import PatternCapability, EnergyLevel, FallbackStrategy


def get_spatial_presets() -> dict[str, LayeredPattern]:
    """
    Get all spatial pattern presets.

    Returns:
        Dict mapping pattern name to LayeredPattern instances.
    """
    return {
        # Spatial patterns (enhanced by ceiling)
        "sp_lightning": lightning(),
        "sp_heartbeat": heartbeat(),
        "sp_ripple": ripple(),
        "sp_fire": fire(),
        "sp_comet": comet(),
        "sp_sunrise": sunrise(),
        "sp_aurora": aurora(),

        # Structural patterns (require both zones)
        "sp_bullseye": bullseye(),
        "sp_vortex": vortex(),
        "sp_portal": portal(),

        # Complementary patterns (different behavior per zone)
        "sp_police": police(),
        "sp_rainbow_breathe": rainbow_breathe(),
    }


# =============================================================================
# SPATIAL PATTERNS (Enhanced by ceiling)
# =============================================================================


def lightning() -> LayeredPattern:
    """
    Lightning strikes from ceiling, illuminates room.

    Ceiling flashes first (the "sky"), perimeter follows 80ms later
    as the room is illuminated.
    """
    return LayeredPattern.create(
        name="sp_lightning",
        description="Lightning strikes from ceiling, illuminates room",
        capability=PatternCapability.ceiling_enhanced(
            tags=["dramatic", "impact", "flash"],
            energy=EnergyLevel.HIGH,
        ),
        ceiling=ceiling().color("white").envelope(attack=0.01, fade=0.1),
        perimeter=perimeter().color("white").envelope(attack=0.01, fade=0.15),
        ceiling_delay=0.0,
        perimeter_delay=0.02,  # ~80ms at 120bpm
        fallback=light("all").color("white").envelope(attack=0.01, fade=0.1),
    )


def heartbeat() -> LayeredPattern:
    """
    Double-pulse heartbeat with ceiling as the heart.

    Ceiling beats at full intensity, perimeter echoes softer and delayed.
    """
    # Double-pulse pattern (lub-dub)
    pulse = light("all ~*2 all ~*12")  # Beat, pause, beat, long pause

    return LayeredPattern.create(
        name="sp_heartbeat",
        description="Double-pulse heartbeat, ceiling leads",
        capability=PatternCapability.ceiling_enhanced(
            tags=["dramatic", "tension", "pulse"],
            energy=EnergyLevel.MEDIUM,
        ),
        ceiling=ceiling().envelope(attack=0.02, fade=0.15).color("red"),
        perimeter=perimeter().envelope(attack=0.02, fade=0.2).color("red"),
        ceiling_delay=0.0,
        perimeter_delay=0.0125,  # ~50ms echo
        fallback=light("all").envelope(attack=0.02, fade=0.15).color("red"),
    )


def ripple() -> LayeredPattern:
    """
    Ripple emanates from ceiling center to perimeter.

    Like a pebble dropped in water - ceiling is the epicenter,
    perimeter receives the expanding wave.
    """
    return LayeredPattern.create(
        name="sp_ripple",
        description="Ripple from ceiling center to perimeter",
        capability=PatternCapability.ceiling_enhanced(
            tags=["impact", "bass", "wave"],
            energy=EnergyLevel.MEDIUM,
        ),
        ceiling=ceiling().color("cyan").envelope(attack=0.02, fade=0.3),
        perimeter=perimeter().seq().color("cyan").envelope(attack=0.05, fade=0.4),
        ceiling_delay=0.0,
        perimeter_delay=0.05,  # Wave travel time
        fallback=light("all").seq().color("cyan").envelope(attack=0.02, fade=0.3),
    )


def fire() -> LayeredPattern:
    """
    Fire effect with ceiling as ember reflection.

    Perimeter has active flames (fast flickering), ceiling gets the
    softer reflected glow as light would bounce off a ceiling.
    """
    # Simulate flickering with fast random pops
    flames = (
        light("perimeter perimeter perimeter perimeter")
        .seq()
        .shuffle()
        .fast(4)
        .envelope(attack=0.01, fade=0.1)
        .color(flash="yellow", fade="orange")
    )

    embers = (
        ceiling()
        .envelope(attack=0.3, fade=0.5, sustain=0.4)
        .slow(2)
        .color("orange")
    )

    return LayeredPattern.create(
        name="sp_fire",
        description="Flames at perimeter, ember glow on ceiling",
        capability=PatternCapability.ceiling_enhanced(
            tags=["ambient", "warm", "organic"],
            energy=EnergyLevel.LOW,
        ),
        ceiling=embers,
        perimeter=flames,
        fallback=flames,  # Just flames if no ceiling
    )


def comet() -> LayeredPattern:
    """
    Comet enters from ceiling, trails around perimeter.

    Ceiling flash marks entry, then chase runs around perimeter.
    """
    entry_flash = ceiling().color("white").envelope(attack=0.01, fade=0.2)

    trail = (
        perimeter()
        .seq()
        .envelope(attack=0.02, fade=0.3, sustain=0.1)
        .color(flash="white", fade="cyan")
    )

    return LayeredPattern.create(
        name="sp_comet",
        description="Comet enters from ceiling, trails around room",
        capability=PatternCapability.ceiling_enhanced(
            tags=["chase", "dramatic", "movement"],
            energy=EnergyLevel.HIGH,
        ),
        ceiling=entry_flash,
        perimeter=trail,
        ceiling_delay=0.0,
        perimeter_delay=0.0625,  # Trail starts after entry
        fallback=trail,  # Just the trail if no ceiling
    )


def sunrise() -> LayeredPattern:
    """
    Slow sunrise: ceiling (sky) leads color transition.

    Very slow color temperature shift from warm to cool,
    with ceiling leading and perimeter following.
    """
    # Warm to cool transition over 8 bars
    sky_transition = cat(
        ceiling().color("red").envelope(attack=0.5, fade=0.5, sustain=0.8),
        ceiling().color("orange").envelope(attack=0.5, fade=0.5, sustain=0.8),
        ceiling().color("yellow").envelope(attack=0.5, fade=0.5, sustain=0.8),
        ceiling().color("white").envelope(attack=0.5, fade=0.5, sustain=0.8),
    ).slow(2)  # 8 bars total

    room_transition = cat(
        perimeter().color("red").envelope(attack=0.5, fade=0.5, sustain=0.6),
        perimeter().color("orange").envelope(attack=0.5, fade=0.5, sustain=0.6),
        perimeter().color("yellow").envelope(attack=0.5, fade=0.5, sustain=0.6),
        perimeter().color("white").envelope(attack=0.5, fade=0.5, sustain=0.6),
    ).slow(2)

    return LayeredPattern.create(
        name="sp_sunrise",
        description="Slow sunrise: ceiling leads color transition",
        capability=PatternCapability.ceiling_enhanced(
            tags=["ambient", "transition", "slow"],
            energy=EnergyLevel.AMBIENT,
        ),
        ceiling=sky_transition,
        perimeter=room_transition,
        perimeter_delay=0.5,  # Room follows sky
        fallback=cat(
            light("all").color("red").envelope(attack=0.5, fade=0.5, sustain=0.7),
            light("all").color("orange").envelope(attack=0.5, fade=0.5, sustain=0.7),
            light("all").color("yellow").envelope(attack=0.5, fade=0.5, sustain=0.7),
            light("all").color("white").envelope(attack=0.5, fade=0.5, sustain=0.7),
        ).slow(2),
    )


def aurora() -> LayeredPattern:
    """
    Aurora borealis: full effect on ceiling, subtle reflection on perimeter.

    Ceiling shows flowing aurora colors, perimeter has muted ambient glow.
    """
    aurora_colors = cat(
        ceiling().color("green").envelope(attack=0.4, fade=0.6, sustain=0.5),
        ceiling().color("cyan").envelope(attack=0.4, fade=0.6, sustain=0.5),
        ceiling().color("blue").envelope(attack=0.4, fade=0.6, sustain=0.5),
        ceiling().color("purple").envelope(attack=0.4, fade=0.6, sustain=0.5),
    ).slow(2)  # 8 bar cycle

    ambient_reflection = (
        perimeter()
        .envelope(attack=0.5, fade=0.5, sustain=0.3)
        .color("cyan")
        .slow(4)
    )

    return LayeredPattern.create(
        name="sp_aurora",
        description="Aurora on ceiling, subtle reflection below",
        capability=PatternCapability.ceiling_enhanced(
            tags=["ambient", "atmospheric", "slow"],
            energy=EnergyLevel.AMBIENT,
        ),
        ceiling=aurora_colors,
        perimeter=ambient_reflection,
        fallback=ambient_reflection,  # Subtle version if no ceiling
    )


# =============================================================================
# STRUCTURAL PATTERNS (Require both zones)
# =============================================================================


def bullseye() -> LayeredPattern:
    """
    Alternating rings: ceiling and perimeter alternate.

    Creates a pulsing target/bullseye effect using the natural ring structure.
    Requires both zones - reinterprets to even/odd if single zone.
    """
    return LayeredPattern.create(
        name="sp_bullseye",
        description="Alternating rings: ceiling ↔ perimeter",
        capability=PatternCapability.requires_dual_zones(
            tags=["geometric", "hypnotic", "pulse"],
            energy=EnergyLevel.MEDIUM,
            allow_reinterpret=True,
        ),
        ceiling=light("ceiling ~").color("red"),
        perimeter=light("~ perimeter").color("blue"),
        reinterpreted=stack(
            light("even ~").color("red"),
            light("~ odd").color("blue"),
        ),
    )


def vortex() -> LayeredPattern:
    """
    Vortex: perimeter spins, ceiling is calm eye of storm.

    Fast chase around perimeter while ceiling pulses slowly as the calm center.
    """
    spinning_edge = (
        perimeter()
        .seq()
        .fast(4)
        .envelope(attack=0.02, fade=0.1)
        .color("cyan")
    )

    calm_eye = (
        ceiling()
        .envelope(attack=0.5, fade=0.5, sustain=0.3)
        .slow(2)
        .color("blue")
    )

    return LayeredPattern.create(
        name="sp_vortex",
        description="Spinning perimeter, calm ceiling eye",
        capability=PatternCapability.ceiling_enhanced(
            tags=["chase", "hypnotic", "energy"],
            energy=EnergyLevel.HIGH,
        ),
        ceiling=calm_eye,
        perimeter=spinning_edge,
        fallback=spinning_edge,  # Just the spin if no ceiling
    )


def portal() -> LayeredPattern:
    """
    Portal: ceiling glows as portal, perimeter reacts with energy.

    Ceiling pulses intensely as a "portal opening", perimeter
    sparkles with emanating energy. Requires both zones.
    """
    portal_glow = (
        ceiling()
        .envelope(attack=0.1, fade=0.3, sustain=0.7)
        .color("purple")
    )

    energy_sparks = (
        light("perimeter perimeter perimeter perimeter")
        .seq()
        .shuffle()
        .envelope(attack=0.01, fade=0.15)
        .color(flash="white", fade="purple")
    )

    return LayeredPattern.create(
        name="sp_portal",
        description="Portal on ceiling, energy emanates to perimeter",
        capability=PatternCapability.requires_dual_zones(
            tags=["dramatic", "scifi", "energy"],
            energy=EnergyLevel.HIGH,
            allow_reinterpret=False,  # This really needs both zones
        ),
        ceiling=portal_glow,
        perimeter=energy_sparks,
    )


# =============================================================================
# COMPLEMENTARY PATTERNS (Different behavior per zone)
# =============================================================================


def police() -> LayeredPattern:
    """
    Police lights: ceiling is red, perimeter is blue, alternating.

    Uses the zone separation for the classic red/blue split.
    Falls back to left/right split if single zone.
    """
    return LayeredPattern.create(
        name="sp_police",
        description="Police lights: ceiling red, perimeter blue",
        capability=PatternCapability.ceiling_enhanced(
            tags=["dramatic", "alert", "strobe"],
            energy=EnergyLevel.HIGH,
        ),
        ceiling=light("ceiling ~").fast(4).color("red"),
        perimeter=light("~ perimeter").fast(4).color("blue"),
        fallback=stack(
            light("left ~").fast(4).color("red"),
            light("~ right").fast(4).color("blue"),
        ),
    )


def rainbow_breathe() -> LayeredPattern:
    """
    Rainbow breathing with complementary colors per zone.

    Both zones breathe together, but ceiling and perimeter
    are offset by 180° in hue for constant color contrast.
    """
    # These colors are roughly complementary
    ceiling_colors = cat(
        ceiling().color("red").envelope(attack=0.4, fade=0.4, sustain=0.5),
        ceiling().color("yellow").envelope(attack=0.4, fade=0.4, sustain=0.5),
        ceiling().color("blue").envelope(attack=0.4, fade=0.4, sustain=0.5),
        ceiling().color("magenta").envelope(attack=0.4, fade=0.4, sustain=0.5),
    )

    perimeter_colors = cat(
        perimeter().color("cyan").envelope(attack=0.4, fade=0.4, sustain=0.5),
        perimeter().color("purple").envelope(attack=0.4, fade=0.4, sustain=0.5),
        perimeter().color("orange").envelope(attack=0.4, fade=0.4, sustain=0.5),
        perimeter().color("green").envelope(attack=0.4, fade=0.4, sustain=0.5),
    )

    return LayeredPattern.create(
        name="sp_rainbow_breathe",
        description="Rainbow breathing with complementary colors per zone",
        capability=PatternCapability.ceiling_enhanced(
            tags=["ambient", "colorful", "pulse"],
            energy=EnergyLevel.LOW,
        ),
        ceiling=ceiling_colors,
        perimeter=perimeter_colors,
        fallback=cat(
            light("all").color("red").envelope(attack=0.4, fade=0.4, sustain=0.5),
            light("all").color("yellow").envelope(attack=0.4, fade=0.4, sustain=0.5),
            light("all").color("blue").envelope(attack=0.4, fade=0.4, sustain=0.5),
            light("all").color("magenta").envelope(attack=0.4, fade=0.4, sustain=0.5),
        ),
    )
