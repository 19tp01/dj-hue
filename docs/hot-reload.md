# Hot-Reload System

> **Purpose**: This document is for Claude Code to track ideas, TODOs, and implementation approaches for the hot-reload system.

## Overview

Hot-reload allows editing pattern files during a live set without restarting. When you save a `.py` pattern file, it's automatically reloaded and the changes take effect immediately.

## Architecture

```
patterns/                     # Watched directory
├── warm_pulse.py            # User pattern files
├── left_right_chase.py
└── ...

         ↓ watchdog monitors

PatternLoader                 # File watcher + loader
    ├── load_pattern_file()   # Import Python module
    ├── start_watching()      # Begin monitoring
    └── on_reload callback    # Notify engine

         ↓ callback

PatternEngine                 # Updates pattern registry
    └── _user_patterns[name] = PatternDef
```

## Pattern File Format

Each pattern file must define a `pattern` or `PATTERN` variable:

```python
# patterns/my_pattern.py
from dj_hue.patterns import PatternDef, GroupEffect, Phaser

pattern = PatternDef(
    name="My Pattern",
    description="A custom pattern",
    group_effects=[
        GroupEffect(
            group_name="all",
            intensity_phaser=Phaser(waveform="sine", beats_per_cycle=2.0),
            base_hue=0.5,
        ),
    ],
)
```

## PatternLoader Implementation

```python
class PatternLoader:
    def __init__(
        self,
        patterns_dir: Path,
        on_reload: Optional[Callable[[str, PatternDef], None]] = None
    ):
        self.patterns_dir = patterns_dir
        self.on_reload = on_reload
        self._observer: Optional[Observer] = None

    def load_pattern_file(self, filepath: Path) -> Optional[PatternDef]:
        """Load a Python pattern file dynamically."""
        spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
        module = importlib.util.module_from_spec(spec)
        # Don't cache in sys.modules for hot-reload
        spec.loader.exec_module(module)

        if hasattr(module, 'pattern'):
            return module.pattern
        elif hasattr(module, 'PATTERN'):
            return module.PATTERN
        return None

    def start_watching(self) -> None:
        """Start watching for file changes."""
        handler = PatternFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.patterns_dir), recursive=True)
        self._observer.start()
```

## Debouncing

File saves often trigger multiple events. We debounce with a 0.5s delay:

```python
class PatternFileHandler(FileSystemEventHandler):
    def __init__(self, loader: PatternLoader):
        self.loader = loader
        self._debounce_time = 0.5
        self._last_reload: dict[str, float] = {}

    def on_modified(self, event: FileModifiedEvent) -> None:
        now = time.time()
        last = self._last_reload.get(str(event.src_path), 0)
        if now - last < self._debounce_time:
            return
        self._last_reload[str(event.src_path)] = now

        # Proceed with reload
        ...
```

## Error Handling

Syntax errors in pattern files shouldn't crash the system:

```python
def load_pattern_file(self, filepath: Path) -> Optional[PatternDef]:
    try:
        # ... load and execute ...
    except SyntaxError as e:
        print(f"[HOT-RELOAD] Syntax error in {filepath.name}: {e}")
        return None
    except Exception as e:
        print(f"[HOT-RELOAD] Error loading {filepath.name}: {e}")
        return None
```

## TODO

- [ ] Add `watchdog` dependency to pyproject.toml
- [ ] Implement PatternLoader class
- [ ] Implement PatternFileHandler with debouncing
- [ ] Add error handling for malformed patterns
- [ ] Add visual feedback when pattern reloads (console message)
- [ ] Consider: audio cue when pattern reloads?

## Ideas

### Validation
Before accepting a reloaded pattern:
- Check required fields are present
- Validate group names exist in setup
- Validate phaser parameters

### Rollback
If a pattern fails to load, keep using the previous version:
```python
def _on_pattern_reload(self, name: str, pattern: PatternDef) -> None:
    if pattern is None:
        print(f"[ENGINE] Keeping previous version of '{name}'")
        return
    self._user_patterns[name] = pattern
```

### Live Preview
When editing, show the pattern on a subset of lights as preview:
```python
preview_mode = True
preview_lights = [0]  # Only show on first light
```

### Pattern Dependencies
If patterns import shared utilities, handle those reloads too:
```python
# patterns/utils.py
def rainbow_hues(n: int) -> list[float]:
    return [i / n for i in range(n)]

# patterns/rainbow.py
from .utils import rainbow_hues
pattern = PatternDef(..., base_hues=rainbow_hues(6))
```

## Dependencies

- `watchdog` - Cross-platform file system monitoring
  - Install: `uv add watchdog`
  - Docs: https://python-watchdog.readthedocs.io/

## Related Files

- `src/dj_hue/patterns/loader.py` - Implementation (to create)
- `patterns/` - User patterns directory (to create)
- `pyproject.toml` - Add watchdog dependency
