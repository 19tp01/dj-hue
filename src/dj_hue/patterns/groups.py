"""
Light grouping system for pattern definitions.

Groups allow patterns to reference logical collections of lights (like "left", "right")
rather than specific indices. This makes patterns portable across different setups.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class ZoneType(Enum):
    """Semantic zone types for light grouping."""
    ALL = "all"
    LEFT = "left"
    RIGHT = "right"
    FRONT = "front"
    BACK = "back"
    CENTER = "center"
    ODD = "odd"
    EVEN = "even"


@dataclass
class LightGroup:
    """
    A named group of light indices.

    Groups are the bridge between pattern definitions (which reference group names)
    and physical lights (which have numeric indices).
    """
    name: str
    light_indices: list[int]
    zone_type: ZoneType | None = None

    def __len__(self) -> int:
        return len(self.light_indices)

    def __iter__(self) -> Iterator[int]:
        return iter(self.light_indices)

    def __contains__(self, light_id: int) -> bool:
        return light_id in self.light_indices


@dataclass
class LightSetup:
    """
    Complete light configuration for a venue/setup.

    A setup defines the total number of lights and how they're organized into groups.
    The same pattern can work with different setups - it just references group names
    and the setup defines which lights are in each group.
    """
    name: str
    total_lights: int
    groups: dict[str, LightGroup] = field(default_factory=dict)

    def get_group(self, name: str) -> LightGroup | None:
        """Get a group by name, or None if not found."""
        return self.groups.get(name)

    def add_group(self, group: LightGroup) -> None:
        """Add a group to this setup."""
        self.groups[group.name] = group

    @classmethod
    def create_default(cls, num_lights: int = 6) -> "LightSetup":
        """
        Create a default setup with common groupings.

        For a 6-light setup, creates:
        - all: [0, 1, 2, 3, 4, 5]
        - left: [0, 1, 2]
        - right: [3, 4, 5]
        - odd: [1, 3, 5]
        - even: [0, 2, 4]
        """
        setup = cls(name="default", total_lights=num_lights)

        # All lights
        setup.groups["all"] = LightGroup(
            name="all",
            light_indices=list(range(num_lights)),
            zone_type=ZoneType.ALL,
        )

        # Left/Right split
        mid = num_lights // 2
        setup.groups["left"] = LightGroup(
            name="left",
            light_indices=list(range(mid)),
            zone_type=ZoneType.LEFT,
        )
        setup.groups["right"] = LightGroup(
            name="right",
            light_indices=list(range(mid, num_lights)),
            zone_type=ZoneType.RIGHT,
        )

        # Odd/Even (for alternating patterns)
        setup.groups["odd"] = LightGroup(
            name="odd",
            light_indices=[i for i in range(num_lights) if i % 2 == 1],
            zone_type=ZoneType.ODD,
        )
        setup.groups["even"] = LightGroup(
            name="even",
            light_indices=[i for i in range(num_lights) if i % 2 == 0],
            zone_type=ZoneType.EVEN,
        )

        # Front/Back (for deeper setups, assumes first half is front)
        if num_lights >= 4:
            front_count = num_lights // 2
            setup.groups["front"] = LightGroup(
                name="front",
                light_indices=list(range(front_count)),
                zone_type=ZoneType.FRONT,
            )
            setup.groups["back"] = LightGroup(
                name="back",
                light_indices=list(range(front_count, num_lights)),
                zone_type=ZoneType.BACK,
            )

        return setup

    @classmethod
    def from_config(cls, config: dict) -> "LightSetup":
        """
        Create a setup from configuration dictionary.

        Expected format:
        {
            "name": "my_setup",
            "total_lights": 8,
            "groups": [
                {"name": "stage_left", "indices": [0, 1]},
                {"name": "stage_right", "indices": [6, 7]},
            ]
        }
        """
        setup = cls(
            name=config.get("name", "custom"),
            total_lights=config.get("total_lights", 6),
        )

        # Add configured groups
        for group_config in config.get("groups", []):
            zone_type = None
            if "zone_type" in group_config:
                try:
                    zone_type = ZoneType(group_config["zone_type"])
                except ValueError:
                    pass

            group = LightGroup(
                name=group_config["name"],
                light_indices=group_config.get("indices", []),
                zone_type=zone_type,
            )
            setup.add_group(group)

        # Always ensure "all" group exists
        if "all" not in setup.groups:
            setup.groups["all"] = LightGroup(
                name="all",
                light_indices=list(range(setup.total_lights)),
                zone_type=ZoneType.ALL,
            )

        return setup

    def validate(self) -> list[str]:
        """
        Validate the setup and return a list of warnings.

        Checks for:
        - Light indices out of range
        - Empty groups
        """
        warnings = []

        for name, group in self.groups.items():
            if not group.light_indices:
                warnings.append(f"Group '{name}' has no lights")

            for idx in group.light_indices:
                if idx < 0 or idx >= self.total_lights:
                    warnings.append(
                        f"Group '{name}' has invalid index {idx} "
                        f"(total_lights={self.total_lights})"
                    )

        return warnings
