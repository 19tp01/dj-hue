# Spatial Pattern System Proposal

> Conversation summary for continuing work on ceiling + perimeter dual-zone lighting patterns.

## Context

The setup has two distinct spatial zones:
- **Ceiling**: OmniGlow strip mounted in a circle on the center ceiling
- **Perimeter**: Regular lights around the edge of the room at eye height

This creates opportunities for spatial lighting effects where patterns can treat each zone differently or use their relationship (center vs. surround, up vs. around).

---

## Proposed New Patterns

We identified 22 patterns, categorized by how they use the dual-zone setup:

### Unified (same on both zones)
| Pattern | Description |
|---------|-------------|
| **Blackout Stabs** | Strategic full darkness → full brightness for impact |
| **Sparkle/Twinkle** | Random individual lights twinkling (can differentiate colors per zone) |

### Complementary (different but harmonious per zone)
| Pattern | Ceiling | Perimeter |
|---------|---------|-----------|
| **Fire/Flame** | Ember glow (slower, dimmer reflection) | Active flames (fast, bright flickering) |
| **Aurora** | Full aurora effect (flowing greens/blues/purples) | Subtle ambient reflection (20-30% intensity) |
| **Candle Flicker** | Reflected glow (subtle, slower) | Direct candle flicker (warm, active) |
| **Theater Chase** | Steady ambient glow | Classic chase rotation |
| **Rainbow Breathe** | Breathing pulse at hue 0° | Same breathing, hue offset 180° |

### Spatial (uses position relationship)
| Pattern | Ceiling Role | Perimeter Role | Timing |
|---------|--------------|----------------|--------|
| **Lightning** | Flash source (sky) | Illumination response | Ceiling first, perimeter 50-100ms later |
| **Heartbeat** | Pulse origin (the "heart") | Echo response (70% intensity) | Ceiling first, perimeter 50ms delay |
| **Comet/Meteor** | Entry flash | Trail chase around room | Sequential |
| **Ripple** | Epicenter | Wave arrival | Ceiling first, perimeter ~200ms later |
| **Sunrise/Sunset** | Leader (sky changes first) | Follower (room catches up) | Ceiling leads by 2-3 seconds |
| **Pendulum** | Gravity indicator (brightness) | Swinging motion | Brightness tied to pendulum position |
| **Spotlight** | Dims to 5% | Focus point at 100% | Inverse relationship |
| **Police** | RED flashes | BLUE flashes | Alternating groups |

### Structural (requires both zones)
| Pattern | Description | Single-Zone Fallback |
|---------|-------------|---------------------|
| **Vortex** | Perimeter spins, ceiling is calm "eye of storm" | Spin only |
| **Gravity Drop** | Energy "falls" from ceiling to perimeter | Just impact flash |
| **Energy Rise** | Energy "rises" from perimeter to ceiling | Just source flash |
| **Portal** | Ceiling glows as portal, perimeter reacts | ❌ Unavailable |
| **Orbit** | Perimeter orbits, ceiling is "sun" | Orbit without sun |
| **Bullseye** | Alternating rings ceiling↔perimeter | Reinterpret as even/odd |

---

## Design Decision: Graceful Degradation

We chose **Option C: Primary + Enhancement Model**:

1. Every pattern has a **primary** single-zone definition that works standalone
2. Patterns can declare **enhancements** that activate when more zones are available
3. A few patterns are marked **requires** and are hidden/disabled without proper hardware
4. Config declares available zones
5. Pattern engine checks requirements at load time and filters/enhances accordingly

### Pattern Metadata

```python
PatternCapability(
    requires_zones=[],              # Hard requirements
    enhanced_by_zones=["ceiling"],  # Soft requirements (better with)
    fallback_strategy=FallbackStrategy.USE_PRIMARY,
    allow_reinterpret=True,         # Can adapt for single-zone?
    tags=["dramatic", "impact"],
    energy=EnergyLevel.HIGH,
)
```

### Fallback Strategies

| Strategy | Behavior |
|----------|----------|
| `USE_PRIMARY` | Run perimeter pattern on all available lights |
| `MERGE_LAYERS` | Combine ceiling+perimeter into single pattern |
| `DISABLE` | Hide pattern if requirements not met |
| `REINTERPRET` | Use alternate single-zone version (e.g., bullseye → even/odd) |

---

## Architecture Changes

### New Files

| File | Purpose |
|------|---------|
| `patterns/zones.py` | `ZoneDefinition`, `ZoneConfig`, `ZonePosition` |
| `patterns/metadata.py` | `PatternCapability`, `FallbackStrategy`, `EnergyLevel` |
| `patterns/registry.py` | `PatternRegistry` with zone-aware filtering |
| `patterns/strudel/layered.py` | `LayeredPattern`, `ZoneLayer` |
| `patterns/strudel/combiner.py` | `combine_zone_layers()` |
| `patterns/strudel/presets_v2.py` | New layered pattern definitions |

### Modified Files

| File | Changes |
|------|---------|
| `patterns/groups.py` | Add optional `zone_config` to `LightSetup` |
| `patterns/strudel/core.py` | Add `zones`, `available_zones` to `LightContext` |
| `patterns/strudel/constructors.py` | Add `zone()` constructor |
| `patterns/engine.py` | Zone-aware rendering, use `PatternRegistry` |

### Config Format

```yaml
name: "living_room_dj"
total_lights: 10

zones:
  ceiling:
    position: ceiling
    groups:
      - name: omniglow
        indices: [0, 1, 2, 3]
    is_primary: false

  perimeter:
    position: wall
    groups:
      - name: left
        indices: [4, 5, 6]
      - name: right
        indices: [7, 8, 9]
    is_primary: true  # Fallback zone
```

### Pattern Definition (New Style)

```python
def lightning() -> LayeredPattern:
    return LayeredPattern(
        name="lightning",
        description="Lightning strikes from ceiling, illuminates room",
        capability=PatternCapability(
            requires_zones=[],
            enhanced_by_zones=["ceiling"],
            fallback_strategy=FallbackStrategy.USE_PRIMARY,
            tags=["dramatic", "impact"],
            energy=EnergyLevel.HIGH,
        ),
        layers={
            "ceiling": ZoneLayer(
                zone="ceiling",
                pattern=light("ceiling").color("white").envelope(attack=0.01, fade=0.1),
                timing_offset=0.0,
            ),
            "perimeter": ZoneLayer(
                zone="perimeter",
                pattern=light("perimeter").color("white").envelope(attack=0.01, fade=0.15),
                timing_offset=0.02,  # 20ms delay
            ),
        },
        fallback_pattern=light("all").color("white").envelope(attack=0.01, fade=0.1),
    )
```

---

## Migration Path

1. **Phase 1**: Add zone infrastructure (non-breaking) - new files, extend existing with optional fields
2. **Phase 2**: Add layered patterns alongside existing - both styles work
3. **Phase 3**: UI integration - show compatibility indicators, filter by availability
4. **Phase 4**: Migrate old patterns (optional) - convert classics to layered format

---

## Open Questions

- [ ] Should zones support more than ceiling/perimeter? (e.g., floor lights)
- [ ] How to handle patterns during zone hot-swap (if lights disconnect)?
- [ ] Should timing offsets be in beats or milliseconds?
- [ ] UI: How prominent should "enhanced with ceiling" badges be?

---

## Next Steps

1. Implement `zones.py` and `metadata.py` (core data structures)
2. Extend `LightSetup` and `LightContext` with zone support
3. Implement `LayeredPattern` and `combine_zone_layers()`
4. Create 3-5 example patterns in new format
5. Update `PatternEngine` to use registry
6. Test with both single-zone and dual-zone configs
