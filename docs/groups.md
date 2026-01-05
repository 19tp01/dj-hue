# Light Grouping System

> **Purpose**: This document is for Claude Code to track ideas, TODOs, and implementation approaches for the light grouping system.

## Overview

The grouping system allows patterns to reference logical groups of lights (like "left", "right", "all") rather than specific light indices. This makes patterns portable across different setups.

## Core Data Structures

### ZoneType

Semantic enum for common zone types:

```python
class ZoneType(Enum):
    ALL = "all"
    LEFT = "left"
    RIGHT = "right"
    FRONT = "front"
    BACK = "back"
    CENTER = "center"
    ODD = "odd"      # Odd-indexed lights
    EVEN = "even"    # Even-indexed lights
```

### LightGroup

A named group of light indices:

```python
@dataclass
class LightGroup:
    name: str
    light_indices: list[int]
    zone_type: Optional[ZoneType] = None

    def __len__(self) -> int:
        return len(self.light_indices)

    def __iter__(self):
        return iter(self.light_indices)
```

### LightSetup

Complete light configuration for a venue/setup:

```python
@dataclass
class LightSetup:
    name: str
    total_lights: int
    groups: dict[str, LightGroup] = field(default_factory=dict)

    @classmethod
    def create_default(cls, num_lights: int = 6) -> "LightSetup":
        """Create a default setup with common groupings."""
        ...
```

## Default Groupings

For a 6-light setup, the default groups are:

| Group | Indices | Description |
|-------|---------|-------------|
| all | [0,1,2,3,4,5] | All lights together |
| left | [0,1,2] | Left half |
| right | [3,4,5] | Right half |
| odd | [1,3,5] | Odd-indexed |
| even | [0,2,4] | Even-indexed |

## Creating a Setup

### In Code

```python
setup = LightSetup.create_default(num_lights=6)

# Add custom group
setup.groups["center"] = LightGroup(
    name="center",
    light_indices=[2, 3],
    zone_type=ZoneType.CENTER
)
```

### In Config (config.yaml)

```yaml
patterns:
  light_setup:
    name: "my_venue"
    total_lights: 8
    groups:
      - name: "stage_left"
        indices: [0, 1]
      - name: "stage_right"
        indices: [6, 7]
      - name: "audience"
        indices: [2, 3, 4, 5]
```

## Resolution at Render Time

Groups are resolved when computing colors, not when defining patterns:

```python
def compute_colors(self) -> dict[int, RGB]:
    for group_effect in pattern.group_effects:
        # Resolve group name to actual indices
        group = self.light_setup.groups.get(group_effect.group_name)
        if not group:
            continue  # Skip unknown groups

        for light_id in group.light_indices:
            # Calculate color for this light
            ...
```

This means the same pattern works with different setups - it just references "left" and the setup defines which lights are "left".

## TODO

- [ ] Implement ZoneType enum
- [ ] Implement LightGroup dataclass
- [ ] Implement LightSetup with create_default()
- [ ] Add config.yaml parsing for custom setups
- [ ] Add validation (no overlapping indices, etc.)

## Ideas

### Overlapping Groups
Currently groups can overlap - the same light can be in multiple groups. The last-applied effect wins. Could add:
- Explicit priority ordering
- Blending between overlapping effects

### Dynamic Groups
Groups that change based on pattern state:
```python
# Alternate which half is "active" each bar
active_group = "left" if bar_position < 2 else "right"
```

### Named Lights
Could support naming individual lights:
```python
setup.lights = {
    0: "front_left",
    1: "front_center",
    2: "front_right",
    ...
}
```

## Related Files

- `src/dj_hue/patterns/groups.py` - Implementation (to create)
- `src/dj_hue/config/schema.py` - Config parsing
- `config.yaml` - User configuration
