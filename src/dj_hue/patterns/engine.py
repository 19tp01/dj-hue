"""
Pattern engine - the core rendering system.

The PatternEngine combines:
- Light groups (which physical lights)
- Pattern definitions (how to animate)
- Color palettes (which colors to use)
- Beat clock (timing)
- Zone configuration (spatial awareness)

And renders RGB colors for each light every frame.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from ..lights.effects import BeatClock, Phaser, RGB
from .groups import LightSetup
from .pattern_def import Pattern, GroupEffect, ColorPalette, HSV
from .registry import PatternRegistry

if TYPE_CHECKING:
    from .strudel import LightPattern, StrudelPatternWrapper, LightContext
    from .strudel.layered import LayeredPattern


def get_builtin_patterns() -> dict[str, Pattern]:
    """Get dictionary of built-in patterns."""
    return {
        "sine_wave": Pattern.create_simple(
            name="Sine Wave",
            waveform="sine",
            beats_per_cycle=2.0,
            phase_spread=True,
            palette=ColorPalette.red(),
            tags=["smooth", "ambient"],
        ),
        "slow_wave": Pattern.create_simple(
            name="Slow Wave",
            waveform="sine",
            beats_per_cycle=4.0,
            phase_spread=True,
            palette=ColorPalette.warm(),
            tags=["slow", "ambient", "chill"],
        ),
        "chase": Pattern.create_chase(
            name="Chase",
            waveform="sawtooth",
            beats_per_cycle=2.0,
            palette=ColorPalette.red(),
        ),
        "fast_chase": Pattern.create_chase(
            name="Fast Chase",
            waveform="sawtooth",
            beats_per_cycle=1.0,
            palette=ColorPalette.cool(),
        ),
        "pulse": Pattern.create_pulse(
            name="Pulse",
            beats_per_cycle=1.0,
            palette=ColorPalette.red(),
        ),
        "strobe": Pattern.create_strobe(
            name="Strobe",
            beats_per_flash=0.25,
            palette=ColorPalette.white(),
        ),
        "left_right": Pattern.create_left_right(
            name="Left Right",
            left_color_index=0,  # Red
            right_color_index=1,  # Blue
            offset=0.5,
        ),
    }


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
    - Pattern registry (built-in + user patterns)
    - Color palette (default or override)
    - Quick actions for momentary effects

    Usage:
        engine = PatternEngine(light_setup)
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

        # Beat clock for timing
        self.beat_clock = BeatClock(bpm=120.0)

        # Pattern registries
        self._builtin_patterns = get_builtin_patterns()
        self._user_patterns: dict[str, Pattern] = {}

        # Current pattern state
        self._current_pattern: Pattern | None = None
        self._current_pattern_index: int = 0
        self._pattern_names: list[str] = list(self._builtin_patterns.keys())

        # Color palette override (None = use pattern's default)
        self._active_palette: ColorPalette | None = None

        # Quick action state
        self._active_quick_action: QuickAction | None = None
        self._quick_action_start_beat: float = 0.0

        # Blackout state
        self._blackout: bool = False

        # Callbacks
        self._on_pattern_change: Callable[[Pattern], None] | None = None

        # Strudel pattern support
        self._strudel_patterns: dict[str, "StrudelPatternWrapper"] = {}
        self._light_context: "LightContext | None" = None

        # Layered spatial pattern support
        self._layered_registry = PatternRegistry(
            light_setup.zone_config if light_setup else None
        )
        self._layered_patterns: dict[str, "LayeredPattern"] = {}

        # Set initial pattern
        if self._pattern_names:
            self._current_pattern = self._builtin_patterns[self._pattern_names[0]]

    @property
    def num_lights(self) -> int:
        return self.light_setup.total_lights

    @property
    def current_pattern(self) -> Pattern | None:
        return self._current_pattern

    @property
    def pattern_names(self) -> list[str]:
        """Get list of all available pattern names."""
        return self._pattern_names

    def get_pattern(self, name: str) -> Pattern | None:
        """Get a pattern by name (user patterns override built-in)."""
        if name in self._user_patterns:
            return self._user_patterns[name]
        return self._builtin_patterns.get(name)

    def register_pattern(self, name: str, pattern: Pattern) -> None:
        """Register a user pattern."""
        self._user_patterns[name] = pattern
        if name not in self._pattern_names:
            self._pattern_names.append(name)

    def register_strudel_pattern(
        self,
        name: str,
        pattern: "LightPattern",
        description: str = "",
        default_color: HSV | None = None,
    ) -> None:
        """
        Register a Strudel-style pattern.

        Args:
            name: Pattern name for selection
            pattern: LightPattern instance
            description: Optional description
            default_color: Default color (defaults to red)
        """
        from .strudel import StrudelPatternWrapper

        wrapper = StrudelPatternWrapper(
            name=name,
            pattern=pattern,
            description=description,
            default_color=default_color or HSV(0.0, 1.0, 1.0),
        )
        self._strudel_patterns[name] = wrapper
        if name not in self._pattern_names:
            self._pattern_names.append(name)

    def reload_strudel_patterns(self) -> int:
        """
        Hot-reload Strudel patterns from disk.

        Returns:
            Number of patterns reloaded
        """
        import importlib
        from . import strudel
        from .strudel import presets

        # Reload the presets module
        importlib.reload(presets)
        # Reload strudel package to pick up new presets reference
        importlib.reload(strudel)

        # Re-import get_strudel_presets after reload
        from .strudel import get_strudel_presets

        # Update existing patterns (keep current selection)
        current_name = self._pattern_names[self._current_pattern_index] if self._pattern_names else None

        new_presets = get_strudel_presets()
        for name, (pattern, description) in new_presets.items():
            from .strudel import StrudelPatternWrapper
            wrapper = StrudelPatternWrapper(
                name=name,
                pattern=pattern,
                description=description,
                default_color=HSV(0.0, 1.0, 1.0),
            )
            self._strudel_patterns[name] = wrapper
            if name not in self._pattern_names:
                self._pattern_names.append(name)

        # Restore selection if possible
        if current_name and current_name in self._pattern_names:
            self._current_pattern_index = self._pattern_names.index(current_name)

        return len(new_presets)

    def register_layered_pattern(self, pattern: "LayeredPattern") -> None:
        """
        Register a layered spatial pattern.

        Args:
            pattern: LayeredPattern instance to register
        """
        self._layered_registry.register(pattern)
        self._layered_patterns[pattern.name] = pattern
        if pattern.name not in self._pattern_names:
            self._pattern_names.append(pattern.name)

    def load_spatial_presets(self) -> int:
        """
        Load all spatial pattern presets.

        Returns:
            Number of patterns loaded
        """
        from .strudel.presets_v2 import get_spatial_presets

        presets = get_spatial_presets()
        for name, pattern in presets.items():
            self.register_layered_pattern(pattern)

        return len(presets)

    def reload_spatial_patterns(self) -> int:
        """
        Hot-reload spatial patterns from disk.

        Returns:
            Number of patterns reloaded
        """
        import importlib
        from .strudel import presets_v2

        # Reload the presets module
        importlib.reload(presets_v2)

        # Re-import and reload
        from .strudel.presets_v2 import get_spatial_presets

        current_name = self._pattern_names[self._current_pattern_index] if self._pattern_names else None

        new_presets = get_spatial_presets()
        for name, pattern in new_presets.items():
            self._layered_registry.register(pattern)
            self._layered_patterns[name] = pattern
            if name not in self._pattern_names:
                self._pattern_names.append(name)

        # Restore selection if possible
        if current_name and current_name in self._pattern_names:
            self._current_pattern_index = self._pattern_names.index(current_name)

        return len(new_presets)

    def get_available_zones(self) -> list[str]:
        """Get list of available zone names."""
        return self.light_setup.available_zones

    def has_dual_zones(self) -> bool:
        """Check if both ceiling and perimeter zones are available."""
        return self.light_setup.has_dual_zones

    def get_layered_pattern_info(self, name: str) -> dict | None:
        """
        Get information about a layered pattern.

        Returns None if pattern not found.
        """
        info = self._layered_registry.get_pattern_info(name)
        if info:
            return {
                "name": info.name,
                "description": info.description,
                "available": info.available,
                "enhanced": info.enhanced,
                "degraded": info.degraded,
                "missing_zones": info.missing_zones,
                "tags": info.tags,
                "energy": info.energy,
            }
        return None

    def _get_light_context(self) -> "LightContext":
        """Get or create the LightContext from current light setup."""
        from .strudel import LightContext

        if self._light_context is None or self._light_context.num_lights != self.num_lights:
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

    def set_pattern(self, name: str) -> bool:
        """
        Set the current pattern by name.

        Returns True if pattern was found and set.
        """
        # Check for layered spatial pattern first
        if name in self._layered_patterns:
            self._current_pattern = None  # Clear classic pattern
            if name in self._pattern_names:
                self._current_pattern_index = self._pattern_names.index(name)
            return True

        # Check for Strudel pattern
        if name in self._strudel_patterns:
            self._current_pattern = None  # Clear classic pattern
            if name in self._pattern_names:
                self._current_pattern_index = self._pattern_names.index(name)
            return True

        # Check for classic pattern
        pattern = self.get_pattern(name)
        if pattern:
            self._current_pattern = pattern
            # Update index for navigation
            if name in self._pattern_names:
                self._current_pattern_index = self._pattern_names.index(name)
            if self._on_pattern_change:
                self._on_pattern_change(pattern)
            return True
        return False

    def set_pattern_by_index(self, idx: int) -> bool:
        """
        Set the current pattern by index (0-based).

        Returns True if index was valid.
        """
        if 0 <= idx < len(self._pattern_names):
            name = self._pattern_names[idx]
            pattern = self.get_pattern(name)
            if pattern:
                self._current_pattern = pattern
                self._current_pattern_index = idx
                if self._on_pattern_change:
                    self._on_pattern_change(pattern)
                return True
        return False

    def next_pattern(self) -> Pattern | None:
        """Advance to the next pattern. Wraps around."""
        if not self._pattern_names:
            return None
        self._current_pattern_index = (self._current_pattern_index + 1) % len(self._pattern_names)
        name = self._pattern_names[self._current_pattern_index]
        self._current_pattern = self.get_pattern(name)
        if self._on_pattern_change and self._current_pattern:
            self._on_pattern_change(self._current_pattern)
        return self._current_pattern

    def prev_pattern(self) -> Pattern | None:
        """Go to the previous pattern. Wraps around."""
        if not self._pattern_names:
            return None
        self._current_pattern_index = (self._current_pattern_index - 1) % len(self._pattern_names)
        name = self._pattern_names[self._current_pattern_index]
        self._current_pattern = self.get_pattern(name)
        if self._on_pattern_change and self._current_pattern:
            self._on_pattern_change(self._current_pattern)
        return self._current_pattern

    def set_palette(self, palette: ColorPalette | None) -> None:
        """
        Set an active palette override.

        If None, patterns will use their default palettes.
        """
        self._active_palette = palette

    def get_active_palette(self) -> ColorPalette | None:
        """Get the currently active palette (or None if using pattern default)."""
        return self._active_palette

    def trigger_quick_action(self, action: QuickAction) -> None:
        """Trigger a quick action (flash, blackout, etc.)."""
        self._active_quick_action = action
        self._quick_action_start_beat = self.beat_clock.beat_position

        if action.action_type == "blackout":
            self._blackout = True

    def release_quick_action(self) -> None:
        """Release any active quick action."""
        if self._active_quick_action and self._active_quick_action.action_type == "blackout":
            self._blackout = False
        self._active_quick_action = None

    def toggle_blackout(self) -> bool:
        """Toggle blackout state. Returns new state."""
        self._blackout = not self._blackout
        return self._blackout

    def update(self, detected_beat: bool = False, detected_bpm: float | None = None) -> None:
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

        current_name = self._pattern_names[self._current_pattern_index] if self._pattern_names else None

        # Check for layered spatial pattern first
        if current_name and current_name in self._layered_patterns:
            return self._compute_layered_pattern_colors(current_name)

        # Check for Strudel pattern
        if current_name and current_name in self._strudel_patterns:
            strudel_wrapper = self._strudel_patterns[current_name]
            context = self._get_light_context()
            return strudel_wrapper.compute_colors(
                beat_position=self.beat_clock.beat_position,
                context=context,
            )

        # Normal pattern rendering (classic system)
        pattern = self._current_pattern
        if not pattern:
            return {i: RGB.black() for i in range(self.num_lights)}

        beat_pos = self.beat_clock.beat_position

        # Get active palette (override or pattern default)
        palette = self._active_palette or pattern.default_palette

        # Build group lookup for resolution
        group_lookup: dict[str, list[int]] = {
            name: list(group.light_indices)
            for name, group in self.light_setup.groups.items()
        }

        colors: dict[int, RGB] = {}

        # Process group effects
        for group_effect in pattern.group_effects:
            group = self.light_setup.get_group(group_effect.group_name)
            if not group:
                continue

            group_size = len(group)

            for position, light_id in enumerate(group.light_indices):
                # Calculate phase offset for this light
                phase_adj = 0.0
                if group_effect.phase_spread and group_size > 1:
                    phase_adj = position / group_size

                # Get intensity
                intensity = self._get_phaser_value(
                    group_effect.intensity_phaser,
                    beat_pos,
                    phase_adj,
                )
                intensity = max(0.0, min(1.0, intensity))

                # Get color from palette
                color = palette.get_color(group_effect.color_index)
                hue = color.hue
                saturation = color.saturation

                # Optional hue modulation
                if group_effect.hue_phaser:
                    hue_mod = self._get_phaser_value(
                        group_effect.hue_phaser,
                        beat_pos,
                        phase_adj,
                    )
                    hue = (hue + hue_mod) % 1.0

                colors[light_id] = RGB.from_hsv(hue, saturation, intensity)

        # Apply independent light overrides
        for light_id, effect in pattern.independent_effects.items():
            intensity = effect.intensity_phaser.get_value(beat_pos)
            intensity = max(0.0, min(1.0, intensity))

            hue = effect.base_hue
            if effect.hue_phaser:
                hue_mod = effect.hue_phaser.get_value(beat_pos)
                hue = (hue + hue_mod) % 1.0

            colors[light_id] = RGB.from_hsv(hue, effect.saturation, intensity)

        # Fill in any missing lights with black
        for i in range(self.num_lights):
            if i not in colors:
                colors[i] = RGB.black()

        return colors

    def _get_phaser_value(
        self,
        phaser: Phaser,
        beat_position: float,
        phase_adjustment: float,
    ) -> float:
        """Get phaser value with temporary phase adjustment."""
        # Temporarily adjust phase offset
        original_offset = phaser.phase_offset
        phaser.phase_offset = (original_offset + phase_adjustment) % 1.0
        value = phaser.get_value(beat_position)
        phaser.phase_offset = original_offset
        return value

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

    def _compute_layered_pattern_colors(self, name: str) -> dict[int, RGB]:
        """
        Compute colors for a layered spatial pattern.

        Gets the effective pattern (with zone fallback applied) and
        renders it using the Strudel rendering system.
        """
        from .strudel import StrudelPatternWrapper

        layered_pattern = self._layered_patterns.get(name)
        if not layered_pattern:
            return {i: RGB.black() for i in range(self.num_lights)}

        # Get available zones
        available_zones = self.light_setup.available_zones

        # Get effective pattern (with fallback applied)
        effective_pattern = layered_pattern.get_effective_pattern(available_zones)
        if not effective_pattern:
            return {i: RGB.black() for i in range(self.num_lights)}

        # Create a temporary wrapper to render
        wrapper = StrudelPatternWrapper(
            name=name,
            pattern=effective_pattern,
            description=layered_pattern.description,
            default_color=HSV(0.0, 1.0, 1.0),
        )

        context = self._get_light_context()
        return wrapper.compute_colors(
            beat_position=self.beat_clock.beat_position,
            context=context,
        )

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
        """Get the name of the current pattern (handles classic, Strudel, and layered)."""
        if not self._pattern_names:
            return "None"
        current_name = self._pattern_names[self._current_pattern_index]
        # For layered patterns, use the registered name
        if current_name in self._layered_patterns:
            return current_name
        # For Strudel patterns, use the registered name
        if current_name in self._strudel_patterns:
            return current_name
        # For classic patterns, use the Pattern object's name if available
        if self._current_pattern:
            return self._current_pattern.name
        return current_name

    def get_status(self) -> dict:
        """Get current engine status for display."""
        current_name = self.get_current_pattern_name()

        # Get pattern type and zone info
        pattern_type = "classic"
        is_degraded = False
        missing_zones: list[str] = []

        if current_name in self._layered_patterns:
            pattern_type = "layered"
            info = self.get_layered_pattern_info(current_name)
            if info:
                is_degraded = info.get("degraded", False)
                missing_zones = info.get("missing_zones", [])
        elif current_name in self._strudel_patterns:
            pattern_type = "strudel"

        return {
            "bpm": self.beat_clock.bpm,
            "beat_position": self.beat_clock.beat_position,
            "bar_position": self.beat_clock.get_bar_position(),
            "pattern": current_name,
            "pattern_type": pattern_type,
            "pattern_index": self._current_pattern_index,
            "palette": (self._active_palette.name if self._active_palette
                       else (self._current_pattern.default_palette.name if self._current_pattern else None)),
            "blackout": self._blackout,
            "quick_action": self._active_quick_action.name if self._active_quick_action else None,
            "available_zones": self.light_setup.available_zones,
            "has_dual_zones": self.has_dual_zones(),
            "is_degraded": is_degraded,
            "missing_zones": missing_zones,
        }
