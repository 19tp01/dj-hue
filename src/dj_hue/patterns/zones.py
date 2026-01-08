"""
Zone system for spatial light groupings.

Zones are higher-level spatial regions (ceiling, perimeter) that contain
one or more light groups. This enables patterns to define different behaviors
for different spatial areas and gracefully degrade when zones are missing.
"""

from dataclasses import dataclass, field
from enum import Enum


class ZonePosition(Enum):
    """Physical position of a zone in the room."""
    CEILING = "ceiling"
    WALL = "wall"          # Eye-level / perimeter
    FLOOR = "floor"        # Future: floor lights


@dataclass
class ZoneDefinition:
    """
    A spatial zone containing one or more light groups.

    Attributes:
        name: Zone identifier (e.g., "ceiling", "perimeter")
        group_names: Names of groups within this zone
        light_indices: Flattened list of all light indices in zone
        position: Physical position (ceiling, wall, floor)
        is_primary: Whether this is the fallback zone for degraded patterns
    """
    name: str
    group_names: list[str]
    light_indices: list[int]
    position: ZonePosition
    is_primary: bool = False

    def __contains__(self, light_id: int) -> bool:
        """Check if a light belongs to this zone."""
        return light_id in self.light_indices

    def __len__(self) -> int:
        """Number of lights in this zone."""
        return len(self.light_indices)


@dataclass
class ZoneConfig:
    """
    Complete zone configuration for a lighting setup.

    Attributes:
        zones: Mapping of zone names to definitions
        primary_zone: Name of the fallback zone (usually "perimeter")
    """
    zones: dict[str, ZoneDefinition] = field(default_factory=dict)
    primary_zone: str = "perimeter"

    def has_zone(self, name: str) -> bool:
        """Check if a zone exists."""
        return name in self.zones

    def get_zone(self, name: str) -> ZoneDefinition | None:
        """Get a zone by name."""
        return self.zones.get(name)

    def available_zones(self) -> list[str]:
        """Get list of available zone names."""
        return list(self.zones.keys())

    def get_primary(self) -> ZoneDefinition | None:
        """Get the primary (fallback) zone."""
        return self.zones.get(self.primary_zone)

    def add_zone(self, zone: ZoneDefinition) -> None:
        """Add a zone to the configuration."""
        self.zones[zone.name] = zone
        if zone.is_primary:
            self.primary_zone = zone.name

    @property
    def has_dual_zones(self) -> bool:
        """True if both ceiling and perimeter zones exist."""
        return "ceiling" in self.zones and "perimeter" in self.zones

    @classmethod
    def from_config(cls, config: dict) -> "ZoneConfig":
        """
        Create ZoneConfig from a configuration dictionary.

        Expected format:
        {
            "zones": {
                "ceiling": {
                    "position": "ceiling",
                    "groups": [
                        {"name": "omniglow", "indices": [0, 1, 2, 3]}
                    ],
                    "is_primary": false
                },
                "perimeter": {
                    "position": "wall",
                    "groups": [
                        {"name": "left", "indices": [4, 5]},
                        {"name": "right", "indices": [6, 7]}
                    ],
                    "is_primary": true
                }
            }
        }
        """
        zone_config = cls()

        for zone_name, zone_data in config.get("zones", {}).items():
            # Parse position
            position_str = zone_data.get("position", "wall")
            try:
                position = ZonePosition(position_str)
            except ValueError:
                position = ZonePosition.WALL

            # Collect all light indices and group names
            group_names = []
            light_indices = []
            for group in zone_data.get("groups", []):
                group_names.append(group["name"])
                light_indices.extend(group.get("indices", []))

            zone = ZoneDefinition(
                name=zone_name,
                group_names=group_names,
                light_indices=light_indices,
                position=position,
                is_primary=zone_data.get("is_primary", False),
            )
            zone_config.add_zone(zone)

        return zone_config

    @classmethod
    def create_single_zone(cls, num_lights: int, zone_name: str = "perimeter") -> "ZoneConfig":
        """
        Create a simple single-zone configuration.

        Useful for setups without ceiling lights.
        """
        zone = ZoneDefinition(
            name=zone_name,
            group_names=["all"],
            light_indices=list(range(num_lights)),
            position=ZonePosition.WALL,
            is_primary=True,
        )
        config = cls()
        config.add_zone(zone)
        return config

    @classmethod
    def create_dual_zone(
        cls,
        ceiling_indices: list[int],
        perimeter_indices: list[int],
    ) -> "ZoneConfig":
        """
        Create a dual-zone configuration with ceiling and perimeter.

        Args:
            ceiling_indices: Light indices for the ceiling zone
            perimeter_indices: Light indices for the perimeter zone
        """
        config = cls()

        config.add_zone(ZoneDefinition(
            name="ceiling",
            group_names=["ceiling"],
            light_indices=ceiling_indices,
            position=ZonePosition.CEILING,
            is_primary=False,
        ))

        config.add_zone(ZoneDefinition(
            name="perimeter",
            group_names=["perimeter"],
            light_indices=perimeter_indices,
            position=ZonePosition.WALL,
            is_primary=True,
        ))

        return config
