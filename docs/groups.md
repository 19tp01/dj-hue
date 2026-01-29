# Light Grouping System

> **Purpose**: This document covers the light grouping system for organizing physical lights into logical groups.

## Overview

The grouping system allows patterns to reference logical groups of lights (like "left", "right", "all") rather than specific light indices. This makes patterns portable across different setups.

There are two related systems:
- **LightSetup / LightGroup**: Used by the PatternEngine and classic patterns
- **LightContext**: Used by Strudel patterns at runtime

Both systems share the same group definitions and work together seamlessly.

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

Complete light configuration for a venue/setup (used by PatternEngine):

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

### LightContext

Runtime context for Strudel patterns:

```python
@dataclass
class LightContext:
    num_lights: int
    groups: dict[str, list[int]]  # Group name -> light indices
    cycle_beats: float = 4.0

    def resolve_group(self, name: str) -> list[int]:
        """Resolve a group name to light indices."""
        return self.groups.get(name, [])

    @classmethod
    def default(cls, num_lights: int = 6) -> "LightContext":
        """Create a default context with standard groups."""
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

Additional groups can be defined for specific setups:

| Group | Example | Description |
|-------|---------|-------------|
| strip | [0,1,2,3] | LED strip lights |
| lamps | [4,5] | Hue lamps |
| front | [0,1] | Front of stage |
| back | [4,5] | Back of stage |

## Creating a Setup

### In Code

```python
from dj_hue.patterns import LightSetup, LightGroup, ZoneType

setup = LightSetup.create_default(num_lights=6)

# Add custom group
setup.groups["center"] = LightGroup(
    name="center",
    light_indices=[2, 3],
    zone_type=ZoneType.CENTER
)

# Add physical groups (for Strudel per-group sequencing)
setup.groups["strip"] = LightGroup(name="strip", light_indices=[0, 1, 2, 3])
setup.groups["lamps"] = LightGroup(name="lamps", light_indices=[4, 5])
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

## Group Resolution

### Classic Patterns

Groups are resolved when computing colors:

```python
def compute_colors(self) -> dict[int, RGB]:
    for group_effect in pattern.group_effects:
        group = self.light_setup.groups.get(group_effect.group_name)
        if not group:
            continue

        for light_id in group.light_indices:
            # Calculate color for this light
            ...
```

### Strudel Patterns

The PatternEngine creates a LightContext from the LightSetup:

```python
def _get_light_context(self) -> LightContext:
    groups = {
        name: list(group.light_indices)
        for name, group in self.light_setup.groups.items()
    }
    return LightContext(num_lights=self.num_lights, groups=groups)
```

Strudel patterns use mini notation that references groups:

```python
from dj_hue.patterns.strudel import light

# These group references are resolved at query time
light("all")      # Resolves to [0, 1, 2, 3, 4, 5]
light("left")     # Resolves to [0, 1, 2]
light("right")    # Resolves to [3, 4, 5]
light("odd")      # Resolves to [1, 3, 5]
light("even")     # Resolves to [0, 2, 4]
```

## Sequencing and Physical Groups

The `seq()` transform in Strudel patterns can sequence lights in two ways:

### Per Physical Group (default)
When "strip" and "lamps" groups are defined, `light("all").seq()` runs the sequence within each physical group simultaneously:

```python
# With strip=[0,1,2,3] and lamps=[4,5]:
# Strip sequences: 0 -> 1 -> 2 -> 3
# Lamps sequence:  4 -> 5
# Both run at the same time
light("all").seq()
```

### All Together
Use `per_group=False` to sequence through ALL lights together:

```python
# Sequences through all 6 lights: 0 -> 1 -> 2 -> 3 -> 4 -> 5
light("all").seq(per_group=False)
```

## Overlapping Groups

Groups can overlap - the same light can be in multiple groups. When patterns target overlapping groups:
- In classic patterns: later GroupEffects override earlier ones
- In Strudel patterns with `stack()`: later patterns take precedence

## Related Files

- `src/dj_hue/patterns/groups.py` - LightGroup, LightSetup, ZoneType
- `src/dj_hue/patterns/strudel/core.py` - LightContext
- `src/dj_hue/patterns/engine.py` - PatternEngine (creates LightContext)
- `config.yaml` - User configuration
