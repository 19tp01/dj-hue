"""
Pattern engine - the core rendering system.

The PatternEngine combines:
- Light groups (which physical lights)
- Strudel patterns (how to animate)
- Beat clock (timing)
- Zone configuration (spatial awareness)

And renders RGB colors for each light every frame.

This is a unified Strudel-only engine - all patterns are LightPattern instances.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..lights.effects import BeatClock, RGB
from .common.groups import LightSetup
from .loader import load_patterns, reload_patterns
from .strudel import (
    LightPattern,
    LightContext,
    PatternScheduler,
    HSV,
)
from .strudel.color import hsv_to_hex
from .strudel.palette import Palette
from .strudel.palettes import get_palette, list_palettes, PALETTES


@dataclass
class QuickAction:
    """Momentary effect that doesn't change the current pattern."""

    name: str
    action_type: str  # "flash", "blackout", "color_bump"
    duration_beats: float = 0.0  # 0 = hold until release
    hue: float | None = None
    intensity: float = 1.0

    @classmethod
    def flash(cls, duration_beats: float = 0.5) -> "QuickAction":
        """Create a white flash action."""
        return cls(
            name="Flash",
            action_type="flash",
            duration_beats=duration_beats,
            intensity=1.0,
        )

    @classmethod
    def blackout(cls) -> "QuickAction":
        """Create a blackout action (hold until release)."""
        return cls(
            name="Blackout",
            action_type="blackout",
            duration_beats=0.0,  # Hold
        )


class PatternEngine:
    """
    Main pattern engine that renders lighting effects.

    The engine coordinates:
    - Beat clock for timing
    - Light setup for group resolution
    - Pattern registry (Strudel patterns only)
    - Quick actions for momentary effects

    Usage:
        engine = PatternEngine(light_setup)
        engine.register("chase", chase_pattern())
        engine.set_pattern("chase")

        # In render loop:
        engine.update(detected_beat, detected_bpm)
        colors = engine.compute_colors()
        for light_id, rgb in colors.items():
            streamer.set_light_color(light_id, rgb.r, rgb.g, rgb.b)
    """

    def __init__(
        self,
        light_setup: LightSetup | None = None,
        patterns_dir: Path | None = None,
    ):
        # Light configuration
        if light_setup is None:
            light_setup = LightSetup.create_default(6)
        self.light_setup = light_setup

        # User patterns directory (for hot-reload)
        self._patterns_dir = patterns_dir

        # Beat clock for timing
        self.beat_clock = BeatClock(bpm=120.0)

        # Single unified pattern registry (Strudel only)
        self._patterns: dict[str, LightPattern] = {}
        self._pattern_descriptions: dict[str, str] = {}
        self._pattern_default_palettes: dict[str, str] = {}  # pattern name -> palette name
        self._pattern_tags: dict[str, list[str]] = {}  # pattern name -> tags
        self._pattern_categories: dict[str, str] = {}  # pattern name -> category
        self._pattern_names: list[str] = []
        self._current_pattern_index: int = 0

        # Current scheduler for rendering
        self._scheduler: PatternScheduler | None = None

        # Palette state
        self._active_palette: Palette | None = None
        self._palette_override: str | None = None  # User-selected, persists across patterns

        # Quick action state
        self._active_quick_action: QuickAction | None = None
        self._quick_action_start_beat: float = 0.0

        # Blackout state
        self._blackout: bool = False

        # Callbacks
        self._on_pattern_change: Callable[[str], None] | None = None

        # Cached light context
        self._light_context: LightContext | None = None

        # Load patterns from library and user directory
        self._load_all_patterns()
        # Initialize palette and scheduler so the first pattern renders immediately.
        self._update_active_palette()
        self._rebuild_scheduler()

    @property
    def num_lights(self) -> int:
        return self.light_setup.total_lights

    @property
    def current_pattern(self) -> LightPattern | None:
        """Get the current pattern."""
        if self._pattern_names and 0 <= self._current_pattern_index < len(self._pattern_names):
            name = self._pattern_names[self._current_pattern_index]
            return self._patterns.get(name)
        return None

    @property
    def pattern_names(self) -> list[str]:
        """Get list of all available pattern names."""
        return self._pattern_names

    def register(
        self,
        name: str,
        pattern: LightPattern,
        description: str = "",
        default_palette: str | None = None,
        tags: list[str] | None = None,
        category: str = "Chill",
    ) -> None:
        """
        Register a pattern.

        Args:
            name: Pattern name for selection
            pattern: LightPattern instance
            description: Optional description
            default_palette: Default palette name for this pattern
            tags: Tags for categorization
            category: Category (Ambient, Buildup, Chill, Upbeat)
        """
        self._patterns[name] = pattern
        self._pattern_descriptions[name] = description
        self._pattern_tags[name] = tags or []
        self._pattern_categories[name] = category
        if default_palette:
            self._pattern_default_palettes[name] = default_palette
        if name not in self._pattern_names:
            self._pattern_names.append(name)

    # Backwards compatibility alias
    def register_strudel_pattern(
        self,
        name: str,
        pattern: LightPattern,
        description: str = "",
        default_color: HSV | None = None,
    ) -> None:
        """
        Register a pattern (backwards compatibility alias).

        Args:
            name: Pattern name for selection
            pattern: LightPattern instance
            description: Optional description
            default_color: Ignored (for backwards compatibility)
        """
        self.register(name, pattern, description)

    def _load_all_patterns(self) -> None:
        """Load patterns from library and user directory."""
        patterns = load_patterns(patterns_dir=self._patterns_dir)
        for name, (pattern, description, default_palette, tags, category) in patterns.items():
            self.register(name, pattern, description, default_palette, tags, category)

    def get_pattern_info(self) -> list[dict]:
        """Get pattern info with tags and category for UI."""
        return [
            {
                "name": name,
                "description": self._pattern_descriptions.get(name, ""),
                "tags": self._pattern_tags.get(name, []),
                "category": self._pattern_categories.get(name, "Chill"),
            }
            for name in self._pattern_names
        ]

    def reload_strudel_patterns(self) -> int:
        """
        Hot-reload all patterns from disk.

        Returns:
            Number of patterns reloaded
        """
        # Remember current selection
        current_name = (
            self._pattern_names[self._current_pattern_index]
            if self._pattern_names
            else None
        )

        # Clear existing patterns
        self._patterns.clear()
        self._pattern_descriptions.clear()
        self._pattern_default_palettes.clear()
        self._pattern_tags.clear()
        self._pattern_categories.clear()
        self._pattern_names.clear()
        self._current_pattern_index = 0

        # Reload all patterns (clears decorator registry and re-imports files)
        patterns = reload_patterns(patterns_dir=self._patterns_dir)
        for name, (pattern, description, default_palette, tags, category) in patterns.items():
            self.register(name, pattern, description, default_palette, tags, category)

        # Restore selection if possible
        if current_name and current_name in self._pattern_names:
            self._current_pattern_index = self._pattern_names.index(current_name)

        # Rebuild scheduler for current pattern (preserves palette override)
        self._update_active_palette()
        self._rebuild_scheduler()

        return len(self._patterns)

    def get_available_zones(self) -> list[str]:
        """Get list of available zone names."""
        return self.light_setup.available_zones

    def has_dual_zones(self) -> bool:
        """Check if both ceiling and perimeter zones are available."""
        return self.light_setup.has_dual_zones

    def _get_light_context(self) -> LightContext:
        """Get or create the LightContext from current light setup."""
        if (
            self._light_context is None
            or self._light_context.num_lights != self.num_lights
        ):
            # Build groups dict from light setup
            groups = {
                name: list(group.light_indices)
                for name, group in self.light_setup.groups.items()
            }

            # Build zones dict from zone configuration
            zones = {}
            available_zones = []
            if self.light_setup.zone_config:
                for zone_name, zone_def in self.light_setup.zone_config.zones.items():
                    zones[zone_name] = zone_def.light_indices
                    available_zones.append(zone_name)
                    # Also register zones as groups so light("ceiling") etc. works
                    groups[zone_name] = zone_def.light_indices

            self._light_context = LightContext(
                num_lights=self.num_lights,
                groups=groups,
                zones=zones,
                available_zones=available_zones,
            )
        return self._light_context

    def _rebuild_scheduler(self) -> None:
        """Rebuild the scheduler for the current pattern."""
        pattern = self.current_pattern
        if pattern:
            self._scheduler = PatternScheduler(
                pattern,
                self._get_light_context(),
                palette=self._active_palette,
            )
        else:
            self._scheduler = None

    def _update_active_palette(self) -> None:
        """Update active palette based on override or pattern default."""
        if self._palette_override:
            # User override takes precedence
            self._active_palette = get_palette(self._palette_override)
        else:
            # Use pattern's default palette
            pattern_name = self.get_current_pattern_name()
            default_name = self._pattern_default_palettes.get(pattern_name)
            if default_name:
                self._active_palette = get_palette(default_name)
            else:
                self._active_palette = None

        # Update scheduler if it exists
        if self._scheduler:
            self._scheduler.set_palette(self._active_palette)

    def set_palette(self, palette_name: str | None) -> bool:
        """
        Set the active palette (user override).

        Args:
            palette_name: Palette name to use, or None to use pattern default

        Returns:
            True if palette was set successfully
        """
        if palette_name is None:
            # Clear override, revert to pattern default
            self._palette_override = None
            self._update_active_palette()
            return True

        palette = get_palette(palette_name)
        if palette is None:
            return False

        self._palette_override = palette_name
        self._active_palette = palette

        # Update scheduler if it exists
        if self._scheduler:
            self._scheduler.set_palette(palette)
        return True

    def get_active_palette(self) -> Palette | None:
        """Get the currently active palette."""
        return self._active_palette

    def get_active_palette_name(self) -> str | None:
        """Get the name of the currently active palette."""
        if self._active_palette:
            return self._active_palette.name
        return None

    def get_palette_override(self) -> str | None:
        """Get the current palette override (None if using pattern default)."""
        return self._palette_override

    def get_available_palettes(self) -> list[dict]:
        """Get list of all available palettes with their colors."""
        result = []
        for name in list_palettes():
            palette = PALETTES.get(name)
            if palette:
                colors = [hsv_to_hex(c) for c in palette.colors]
                result.append({"name": name, "colors": colors})
        return result

    def set_pattern(self, name: str) -> bool:
        """
        Set the current pattern by name.

        Returns True if pattern was found and set.
        """
        if name not in self._patterns:
            return False

        if name in self._pattern_names:
            self._current_pattern_index = self._pattern_names.index(name)
            self._update_active_palette()  # Load pattern's palette (unless override)
            self._rebuild_scheduler()
            if self._on_pattern_change:
                self._on_pattern_change(name)
            return True
        return False

    def set_pattern_by_index(self, idx: int) -> bool:
        """
        Set the current pattern by index (0-based).

        Returns True if index was valid.
        """
        if 0 <= idx < len(self._pattern_names):
            self._current_pattern_index = idx
            self._update_active_palette()
            self._rebuild_scheduler()
            if self._on_pattern_change:
                self._on_pattern_change(self._pattern_names[idx])
            return True
        return False

    def next_pattern(self) -> LightPattern | None:
        """Advance to the next pattern. Wraps around."""
        if not self._pattern_names:
            return None
        self._current_pattern_index = (self._current_pattern_index + 1) % len(
            self._pattern_names
        )
        self._update_active_palette()
        self._rebuild_scheduler()
        if self._on_pattern_change:
            self._on_pattern_change(self._pattern_names[self._current_pattern_index])
        return self.current_pattern

    def prev_pattern(self) -> LightPattern | None:
        """Go to the previous pattern. Wraps around."""
        if not self._pattern_names:
            return None
        self._current_pattern_index = (self._current_pattern_index - 1) % len(
            self._pattern_names
        )
        self._update_active_palette()
        self._rebuild_scheduler()
        if self._on_pattern_change:
            self._on_pattern_change(self._pattern_names[self._current_pattern_index])
        return self.current_pattern

    def trigger_quick_action(self, action: QuickAction) -> None:
        """Trigger a quick action (flash, blackout, etc.)."""
        self._active_quick_action = action
        self._quick_action_start_beat = self.beat_clock.beat_position

        if action.action_type == "blackout":
            self._blackout = True

    def release_quick_action(self) -> None:
        """Release any active quick action."""
        if (
            self._active_quick_action
            and self._active_quick_action.action_type == "blackout"
        ):
            self._blackout = False
        self._active_quick_action = None

    def toggle_blackout(self) -> bool:
        """Toggle blackout state. Returns new state."""
        self._blackout = not self._blackout
        return self._blackout

    def update(
        self, detected_beat: bool = False, detected_bpm: float | None = None
    ) -> None:
        """
        Update the beat clock. Call this every frame.

        Args:
            detected_beat: True if a beat was just detected
            detected_bpm: BPM from beat detector (for syncing)
        """
        self.beat_clock.update(detected_beat, detected_bpm)

        # Check if quick action has expired
        if self._active_quick_action and self._active_quick_action.duration_beats > 0:
            elapsed = self.beat_clock.beat_position - self._quick_action_start_beat
            if elapsed >= self._active_quick_action.duration_beats:
                self._active_quick_action = None

    def compute_colors(self) -> dict[int, RGB]:
        """
        Compute RGB colors for all lights.

        This is the main render method - call it every frame to get
        the current color for each light.
        """
        # Handle blackout
        if self._blackout:
            return {i: RGB.black() for i in range(self.num_lights)}

        # Handle quick actions
        if self._active_quick_action:
            return self._compute_quick_action_colors()

        # Render current pattern through scheduler
        if self._scheduler is None:
            return {i: RGB.black() for i in range(self.num_lights)}

        return self._scheduler.compute_colors(self.beat_clock.beat_position)

    def _compute_quick_action_colors(self) -> dict[int, RGB]:
        """Compute colors for active quick action."""
        action = self._active_quick_action
        if not action:
            return {i: RGB.black() for i in range(self.num_lights)}

        if action.action_type == "flash":
            # White flash
            return {i: RGB.white() for i in range(self.num_lights)}

        elif action.action_type == "blackout":
            return {i: RGB.black() for i in range(self.num_lights)}

        elif action.action_type == "color_bump" and action.hue is not None:
            color = RGB.from_hsv(action.hue, 1.0, action.intensity)
            return {i: color for i in range(self.num_lights)}

        # Default: black
        return {i: RGB.black() for i in range(self.num_lights)}

    def get_bpm(self) -> float:
        """Get current BPM."""
        return self.beat_clock.bpm

    def get_beat_position(self) -> float:
        """Get current beat position."""
        return self.beat_clock.beat_position

    def reset_beat(self) -> None:
        """Reset beat position to 0."""
        self.beat_clock.reset()

    def get_current_pattern_name(self) -> str:
        """Get the name of the current pattern."""
        if not self._pattern_names:
            return "None"
        return self._pattern_names[self._current_pattern_index]

    def get_current_pattern_description(self) -> str:
        """Get the description of the current pattern."""
        name = self.get_current_pattern_name()
        return self._pattern_descriptions.get(name, "")

    def get_status(self) -> dict:
        """Get current engine status for display."""
        current_name = self.get_current_pattern_name()

        return {
            "bpm": self.beat_clock.bpm,
            "beat_position": self.beat_clock.beat_position,
            "bar_position": self.beat_clock.get_bar_position(),
            "pattern": current_name,
            "pattern_index": self._current_pattern_index,
            "blackout": self._blackout,
            "quick_action": (
                self._active_quick_action.name if self._active_quick_action else None
            ),
            "available_zones": self.light_setup.available_zones,
            "has_dual_zones": self.has_dual_zones(),
            "palette": self.get_active_palette_name(),
            "palette_override": self._palette_override,
        }
