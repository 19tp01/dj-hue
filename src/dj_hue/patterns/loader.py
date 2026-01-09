"""
Pattern loader with directory scanning.

Loads patterns from a user-specified patterns directory.
The directory is scanned for .py files containing @pattern-decorated functions.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .strudel import LightPattern


def load_patterns(
    patterns_dir: Path | None = None,
) -> dict[str, tuple["LightPattern", str, str | None]]:
    """
    Load all patterns from directory.

    Args:
        patterns_dir: Directory containing pattern files (e.g., patterns/ in project root)

    Returns:
        Dict mapping pattern name to (LightPattern, description, default_palette).
    """
    from .decorator import clear_registry, get_registered_patterns

    # Clear registry for fresh load (enables hot-reload)
    clear_registry()

    # Import patterns if directory exists
    if patterns_dir and patterns_dir.exists():
        _import_patterns_directory(patterns_dir)

    return get_registered_patterns()


def reload_patterns(
    patterns_dir: Path | None = None,
) -> dict[str, tuple["LightPattern", str, str | None]]:
    """
    Reload all patterns (for hot-reload).

    Clears cached modules and re-imports everything.
    """
    from .decorator import clear_registry, get_registered_patterns

    # Clear registry
    clear_registry()

    # Clear and reload patterns
    _clear_pattern_module_cache()
    if patterns_dir and patterns_dir.exists():
        _import_patterns_directory(patterns_dir)

    return get_registered_patterns()


def _import_patterns_directory(directory: Path) -> None:
    """Import pattern files from a directory."""
    for py_file in sorted(directory.glob("**/*.py")):
        if py_file.name.startswith("_"):
            continue
        _import_pattern_file(py_file)


def _import_pattern_file(file_path: Path) -> None:
    """Import a single pattern Python file."""
    # Generate unique module name based on path
    module_name = f"dj_hue_pattern_{file_path.stem}_{hash(str(file_path)) & 0xFFFFFFFF:08x}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        # Log but don't crash - allows partial loading
        print(f"Warning: Failed to import {file_path}: {e}")


def _clear_pattern_module_cache() -> None:
    """Remove cached pattern modules (for hot-reload)."""
    prefix = "dj_hue_pattern_"
    to_remove = [
        name
        for name in sys.modules.keys()
        if name.startswith(prefix)
    ]
    for name in to_remove:
        del sys.modules[name]
