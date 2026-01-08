"""
Hot-reload system for pattern files.

Watches a directory for Python pattern files and reloads them automatically
when they change. This allows editing patterns during a live set.
"""

import importlib.util
import time
from pathlib import Path
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from .pattern_def import PatternDef


class PatternLoader:
    """
    Loads and hot-reloads pattern files from a directory.

    Pattern files are Python files that define a `pattern` or `PATTERN` variable
    of type PatternDef.

    Usage:
        loader = PatternLoader(
            patterns_dir=Path("patterns"),
            on_reload=lambda name, pattern: engine.register_pattern(name, pattern),
        )
        loader.load_all()        # Initial load
        loader.start_watching()  # Begin hot-reload

        # ... later ...
        loader.stop_watching()
    """

    def __init__(
        self,
        patterns_dir: Path,
        on_reload: Callable[[str, PatternDef], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ):
        """
        Initialize the pattern loader.

        Args:
            patterns_dir: Directory to watch for pattern files
            on_reload: Callback when a pattern is loaded/reloaded (name, pattern)
            on_error: Callback when a pattern fails to load (filename, exception)
        """
        self.patterns_dir = Path(patterns_dir)
        self.on_reload = on_reload
        self.on_error = on_error
        self._patterns: dict[str, PatternDef] = {}
        self._observer: Observer | None = None

    @property
    def patterns(self) -> dict[str, PatternDef]:
        """Get all loaded patterns."""
        return self._patterns.copy()

    def load_pattern_file(self, filepath: Path) -> PatternDef | None:
        """
        Load a Python pattern file.

        Pattern files should define a `pattern` or `PATTERN` variable.

        Args:
            filepath: Path to the Python file

        Returns:
            PatternDef if successful, None if file doesn't define a pattern
        """
        if not filepath.exists():
            return None

        if filepath.suffix != ".py":
            return None

        # Skip __init__.py and similar
        if filepath.stem.startswith("_"):
            return None

        try:
            # Load module without caching (enables hot-reload)
            spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for pattern definition
            pattern = None
            if hasattr(module, "pattern"):
                pattern = module.pattern
            elif hasattr(module, "PATTERN"):
                pattern = module.PATTERN

            if pattern is None:
                print(f"[LOADER] Warning: {filepath.name} has no 'pattern' definition")
                return None

            if not isinstance(pattern, PatternDef):
                print(f"[LOADER] Warning: {filepath.name} 'pattern' is not a PatternDef")
                return None

            return pattern

        except SyntaxError as e:
            print(f"[LOADER] Syntax error in {filepath.name}: {e}")
            if self.on_error:
                self.on_error(filepath.name, e)
            return None
        except Exception as e:
            print(f"[LOADER] Error loading {filepath.name}: {e}")
            if self.on_error:
                self.on_error(filepath.name, e)
            return None

    def load_all(self) -> dict[str, PatternDef]:
        """
        Load all pattern files from the patterns directory.

        Returns:
            Dictionary of pattern name -> PatternDef
        """
        if not self.patterns_dir.exists():
            print(f"[LOADER] Patterns directory does not exist: {self.patterns_dir}")
            return {}

        loaded = {}
        for filepath in self.patterns_dir.glob("**/*.py"):
            # Skip __pycache__ and similar
            if "__pycache__" in str(filepath):
                continue

            pattern = self.load_pattern_file(filepath)
            if pattern:
                name = filepath.stem
                loaded[name] = pattern
                self._patterns[name] = pattern

                if self.on_reload:
                    self.on_reload(name, pattern)

                print(f"[LOADER] Loaded pattern: {pattern.name} ({name})")

        return loaded

    def reload_file(self, filepath: Path) -> bool:
        """
        Reload a specific pattern file.

        Returns:
            True if pattern was successfully reloaded
        """
        pattern = self.load_pattern_file(filepath)
        if pattern:
            name = filepath.stem
            self._patterns[name] = pattern

            if self.on_reload:
                self.on_reload(name, pattern)

            print(f"[LOADER] Reloaded pattern: {pattern.name} ({name})")
            return True
        return False

    def start_watching(self) -> None:
        """Start watching the patterns directory for changes."""
        if self._observer is not None:
            return  # Already watching

        if not self.patterns_dir.exists():
            print(f"[LOADER] Cannot watch - directory does not exist: {self.patterns_dir}")
            return

        handler = _PatternFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.patterns_dir), recursive=True)
        self._observer.start()
        print(f"[LOADER] Watching for pattern changes: {self.patterns_dir}")

    def stop_watching(self) -> None:
        """Stop watching for file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            print("[LOADER] Stopped watching for pattern changes")


class _PatternFileHandler(FileSystemEventHandler):
    """
    Handles file system events for pattern files.

    Includes debouncing to handle rapid saves (editors often trigger multiple events).
    """

    def __init__(self, loader: PatternLoader):
        self.loader = loader
        self._debounce_time = 0.5  # seconds
        self._last_event: dict[str, float] = {}

    def _should_process(self, filepath: str) -> bool:
        """Check if we should process this event (debouncing)."""
        now = time.time()
        last = self._last_event.get(filepath, 0)
        if now - last < self._debounce_time:
            return False
        self._last_event[filepath] = now
        return True

    def _handle_file(self, event) -> None:
        """Handle a file modification or creation."""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Only process Python files
        if filepath.suffix != ".py":
            return

        # Skip cache and hidden files
        if "__pycache__" in str(filepath) or filepath.stem.startswith("."):
            return

        # Debounce
        if not self._should_process(str(filepath)):
            return

        # Reload the pattern
        print(f"[HOT-RELOAD] Detected change: {filepath.name}")
        self.loader.reload_file(filepath)

    def on_modified(self, event: FileModifiedEvent) -> None:
        self._handle_file(event)

    def on_created(self, event: FileCreatedEvent) -> None:
        self._handle_file(event)
