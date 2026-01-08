"""
Pattern loader with directory scanning.

Loads patterns from:
1. Built-in library/ directory (as package modules)
2. User patterns/ directory (as standalone files)

Both directories are scanned for .py files containing @pattern-decorated functions.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .strudel import LightPattern

# Built-in library module names
_LIBRARY_MODULES = [
    "dj_hue.patterns.library.flash",
    "dj_hue.patterns.library.chase",
    "dj_hue.patterns.library.strobe",
    "dj_hue.patterns.library.ambient",
    "dj_hue.patterns.library.energy",
    "dj_hue.patterns.library.signature",
    "dj_hue.patterns.library.rainbow",
    "dj_hue.patterns.library.autonomous",
    "dj_hue.patterns.library.classic",
    "dj_hue.patterns.library.spatial",
]


def load_patterns(
    library_dir: Path | None = None,
    user_dir: Path | None = None,
) -> dict[str, tuple["LightPattern", str]]:
    """
    Load all patterns from directories.

    Args:
        library_dir: Ignored (library is loaded as package modules)
        user_dir: User patterns directory (optional, e.g., patterns/ in project root)

    Returns:
        Dict mapping pattern name to (LightPattern, description).
    """
    from .decorator import clear_registry, get_registered_patterns

    # Clear registry for fresh load (enables hot-reload)
    clear_registry()

    # Import built-in library modules (these are proper package modules)
    _import_library_modules()

    # Import user patterns if directory exists
    if user_dir and user_dir.exists():
        _import_user_directory(user_dir)

    return get_registered_patterns()


def reload_patterns(
    library_dir: Path | None = None,
    user_dir: Path | None = None,
) -> dict[str, tuple["LightPattern", str]]:
    """
    Reload all patterns (for hot-reload).

    Clears cached modules and re-imports everything.
    """
    from .decorator import clear_registry, get_registered_patterns

    # Clear registry
    clear_registry()

    # Reload library modules (re-runs @pattern decorators)
    for module_name in _LIBRARY_MODULES:
        if module_name in sys.modules:
            try:
                importlib.reload(sys.modules[module_name])
            except Exception as e:
                print(f"Warning: Failed to reload {module_name}: {e}")
        else:
            # Module not yet loaded, import it
            try:
                importlib.import_module(module_name)
            except Exception as e:
                print(f"Warning: Failed to import {module_name}: {e}")

    # Clear and reload user patterns
    _clear_user_module_cache()
    if user_dir and user_dir.exists():
        _import_user_directory(user_dir)

    return get_registered_patterns()


def _import_library_modules() -> None:
    """Import built-in library modules using standard import system."""
    for module_name in _LIBRARY_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f"Warning: Failed to import {module_name}: {e}")


def _import_user_directory(directory: Path) -> None:
    """Import user pattern files from a directory."""
    for py_file in sorted(directory.glob("**/*.py")):
        if py_file.name.startswith("_"):
            continue
        _import_user_file(py_file)


def _import_user_file(file_path: Path) -> None:
    """Import a single user Python file."""
    # Generate unique module name based on path
    module_name = f"dj_hue_user_pattern_{file_path.stem}_{hash(str(file_path)) & 0xFFFFFFFF:08x}"

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


def _clear_user_module_cache() -> None:
    """Remove cached user pattern modules (for hot-reload)."""
    prefix = "dj_hue_user_pattern_"
    to_remove = [
        name
        for name in sys.modules.keys()
        if name.startswith(prefix)
    ]
    for name in to_remove:
        del sys.modules[name]
