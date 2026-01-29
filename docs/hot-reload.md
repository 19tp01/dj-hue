# Hot-Reload System

> **Purpose**: This document covers the hot-reload system for live pattern editing.

## Overview

Hot-reload allows editing pattern files during a live set without restarting. When you save a `.py` pattern file, it's automatically reloaded and the changes take effect immediately.

There are two hot-reload mechanisms:
1. **User pattern files** (`patterns/`) - Classic Pattern format files watched by PatternLoader
2. **Strudel presets** (`strudel/presets.py`) - Can be reloaded via `engine.reload_strudel_patterns()`

## Architecture

```
patterns/                     # Watched directory
├── warm_pulse.py            # User pattern files (classic format)
├── my_custom.py
└── examples/
    └── ...

         ↓ watchdog monitors

PatternLoader                 # File watcher + loader
    ├── load_pattern_file()   # Import Python module
    ├── start_watching()      # Begin monitoring
    └── on_reload callback    # Notify engine

         ↓ callback

PatternEngine                 # Updates pattern registry
    └── _user_patterns[name] = Pattern
```

## User Pattern Files (Classic Format)

Each classic pattern file must define a `pattern` or `PATTERN` variable:

```python
# patterns/my_pattern.py
from dj_hue.patterns import Pattern, GroupEffect, Phaser, ColorPalette, HSV

pattern = Pattern(
    name="My Pattern",
    description="A custom pattern",
    group_effects=[
        GroupEffect(
            group_name="all",
            intensity_phaser=Phaser(waveform="sine", beats_per_cycle=2.0),
            color_index=0,
        ),
    ],
    default_palette=ColorPalette(colors=[HSV(0.5, 1, 1)]),
)
```

## Strudel Preset Hot-Reload

Strudel presets in `strudel/presets.py` can be hot-reloaded:

```python
# In your application code
count = engine.reload_strudel_patterns()
print(f"Reloaded {count} Strudel patterns")
```

This reloads the presets module and updates all registered Strudel patterns while preserving the current pattern selection.

## PatternLoader Implementation

```python
class PatternLoader:
    def __init__(
        self,
        patterns_dir: Path,
        on_reload: Optional[Callable[[str, Pattern], None]] = None
    ):
        self.patterns_dir = patterns_dir
        self.on_reload = on_reload
        self._observer: Optional[Observer] = None

    def load_pattern_file(self, filepath: Path) -> Optional[Pattern]:
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
def load_pattern_file(self, filepath: Path) -> Optional[Pattern]:
    try:
        # ... load and execute ...
    except SyntaxError as e:
        print(f"[HOT-RELOAD] Syntax error in {filepath.name}: {e}")
        return None
    except Exception as e:
        print(f"[HOT-RELOAD] Error loading {filepath.name}: {e}")
        return None
```

If a pattern fails to load, the previous version is kept:

```python
def _on_pattern_reload(self, name: str, pattern: Pattern) -> None:
    if pattern is None:
        print(f"[ENGINE] Keeping previous version of '{name}'")
        return
    self._user_patterns[name] = pattern
```

## Live Editing Workflow

1. Start DJ-Hue in pattern mode
2. Open a pattern file in your editor
3. Make changes and save
4. Watch the lights update immediately
5. If there's an error, check the console - previous pattern keeps running

## Dependencies

- `watchdog` - Cross-platform file system monitoring
  - Install: `uv add watchdog`
  - Docs: https://python-watchdog.readthedocs.io/

## Related Files

- `src/dj_hue/patterns/loader.py` - PatternLoader implementation
- `src/dj_hue/patterns/engine.py` - `reload_strudel_patterns()` method
- `patterns/` - User patterns directory
- `src/dj_hue/patterns/strudel/presets.py` - Strudel presets
