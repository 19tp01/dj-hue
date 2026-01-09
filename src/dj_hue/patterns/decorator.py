"""
Pattern decorator for auto-discovery.

Usage:
    from dj_hue.patterns.decorator import pattern

    @pattern("my_pattern", "Description of pattern", tags=["flash"])
    def my_pattern() -> LightPattern:
        return light("all").color("red")
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .strudel import LightPattern


@dataclass
class PatternMeta:
    """Metadata for a registered pattern."""

    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    default_palette: str | None = None


# Global registry: name -> (factory_function, metadata)
_REGISTRY: dict[str, tuple[Callable[[], "LightPattern"], PatternMeta]] = {}


def pattern(
    name: str,
    description: str = "",
    tags: list[str] | None = None,
    palette: str | None = None,
) -> Callable[[Callable[[], "LightPattern"]], Callable[[], "LightPattern"]]:
    """
    Register a pattern function with the global registry.

    Args:
        name: Unique pattern name (displayed in UI)
        description: Human-readable description
        tags: Optional tags for filtering (e.g., ["flash", "strobe"])
        palette: Default palette name for this pattern (e.g., "fire", "neon")

    Example:
        @pattern("s_stagger", "Random sequential flash", tags=["flash"], palette="fire")
        def stagger_flash() -> LightPattern:
            return light("all").seq().shuffle().color(palette.random)
    """

    def decorator(
        fn: Callable[[], "LightPattern"],
    ) -> Callable[[], "LightPattern"]:
        meta = PatternMeta(
            name=name,
            description=description,
            tags=tags or [],
            default_palette=palette,
        )
        _REGISTRY[name] = (fn, meta)
        return fn

    return decorator


def get_registered_patterns() -> dict[str, tuple["LightPattern", str, str | None]]:
    """
    Get all registered patterns, instantiated.

    Returns:
        Dict mapping name to (LightPattern instance, description, default_palette).
    """
    from .strudel import LightPattern

    result: dict[str, tuple[LightPattern, str, str | None]] = {}
    for name, (fn, meta) in _REGISTRY.items():
        try:
            pattern_instance = fn()
            result[name] = (pattern_instance, meta.description, meta.default_palette)
        except Exception as e:
            # Log but don't crash - allows partial loading
            print(f"Warning: Failed to instantiate pattern '{name}': {e}")
    return result


def get_registry() -> dict[str, tuple[Callable[[], "LightPattern"], PatternMeta]]:
    """Get the raw registry (for inspection/debugging)."""
    return _REGISTRY.copy()


def clear_registry() -> None:
    """Clear the registry (for hot-reload)."""
    _REGISTRY.clear()
