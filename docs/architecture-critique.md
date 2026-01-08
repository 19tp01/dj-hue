# DJ-Hue Architecture Critique (Music -> Lighting)

This document summarizes an architectural critique of the Strudel system and the broader DJ-Hue codebase, with a focus on "lego-like" composability for complex, versatile light patterns.

Scope:
- docs/strudel-system.md
- Pattern engine, Strudel core, spatial layering, scheduler, CLI integration, and streaming modules

## Executive Summary

The Strudel pattern core is strong and already lego-like (pure functions, immutable transforms, query-based patterns). The weakest spots are the seams between pattern systems (classic vs Strudel vs layered), time-unit inconsistencies, and lifecycle/state handling in the scheduler. These seams create "jank" in selection, timing, and envelope behavior, and make cross-pattern composition harder than it needs to be.

Key risks to extensibility:
- Layered patterns rebuild schedulers per frame, losing cross-frame state.
- Time units for spatial delays are described as beats but implemented in cycles.
- Pattern selection and navigation are only fully correct for classic patterns.
- Multiple pattern models live side-by-side without a unified render interface.

## Architecture Map (Current)

```
MIDI clock / beat detector
  -> BeatClock
    -> PatternEngine
       -> Classic Pattern (GroupEffect + Phaser) OR
       -> Strudel Pattern (LightPattern -> PatternScheduler) OR
       -> Layered Pattern (LayeredPattern -> LightPattern -> PatternScheduler)
    -> RGB colors
  -> Hue streaming
```

This is a hybrid architecture: two pattern systems (classic and Strudel) plus a layered spatial system on top of Strudel. Each system has its own selection and render logic.

## Detailed Findings

### F1. Layered patterns recreate a scheduler every frame (High)
- Where: `src/dj_hue/patterns/engine.py:646` (creates a new `StrudelPatternWrapper` each call)
- Why it matters: `StrudelPatternWrapper` owns a `PatternScheduler` with `_active_events` state to sustain envelopes across frames (`src/dj_hue/patterns/strudel/scheduler.py:139`). Recreating the wrapper resets this state every frame, which can truncate envelopes, break release tails, and cause brightness flicker.
- Impact on "lego" composition: Layered patterns cannot reliably stack long envelopes or modulators, making complex patterns unpredictable.
- Suggested direction: Cache the wrapper or scheduler per layered pattern, similar to how Strudel patterns are cached in `register_strudel_pattern()`.

### F2. Time-unit mismatch (beats vs cycles) in spatial delays (High)
- Where:
  - `src/dj_hue/patterns/strudel/spatial/layered.py:29` (`timing_offset` documented as beats)
  - `src/dj_hue/patterns/strudel/spatial/combiner.py:90` (`delay_beats` documented as beats)
  - `src/dj_hue/patterns/strudel/core/pattern.py:82` (`early/late` shift is in cycles)
- Why it matters: Spatial delays are described as "beats" but are implemented as "cycles" (1 cycle = 4 beats). This introduces 4x timing errors in a 4/4 context and makes it hard to reason about timing and sync.
- Impact on "lego" composition: Timing offsets are the glue for spatial patterns; inconsistent units make those patterns unreliable and hard to combine.
- Suggested direction: Explicitly encode time units in APIs or provide helpers (e.g., `late_beats()` or `beats_to_cycles()`), and use `LightContext.cycle_beats` consistently.

### F3. Pattern selection by index only works for classic patterns (Medium)
- Where:
  - `src/dj_hue/patterns/engine.py:421` (`set_pattern_by_index` only sets classic patterns)
  - `src/dj_hue/cli/midi_pattern_mode.py:458` (pattern selector calls `set_pattern_by_index`)
- Why it matters: Strudel and layered patterns are listed in `_pattern_names` but cannot be selected via the numeric UI because `set_pattern_by_index()` returns False unless the name resolves to a classic `Pattern`.
- Impact: Inconsistent UI and selection logic reduce confidence in live use and make Strudel patterns feel like second-class citizens.
- Suggested direction: Make selection logic operate on a unified pattern registry instead of only classic `Pattern`.

### F4. Multiple pattern models without a unified render interface (Medium)
- Where: `src/dj_hue/patterns/engine.py:142-172`
- Why it matters: Classic patterns and Strudel patterns have different render paths, and layered patterns are a third path. This splits composition, metadata, and selection logic across different objects.
- Impact on "lego" composition: You cannot directly combine a classic pattern with a Strudel pattern; they live in different universes.
- Suggested direction: Choose a single renderable pattern interface (e.g., `LightPattern` query API) and wrap the classic system as a query-based adaptor so everything composes through one pipeline.

### F5. Event compositing is "last write wins" (Medium)
- Where: `src/dj_hue/patterns/strudel/scheduler.py:91` (writes directly into `colors` dict)
- Why it matters: `stack()` just concatenates events, and the scheduler overwrites the per-light color with the last event in iteration order. There is no blending, priority, or explicit composition strategy.
- Impact on "lego" composition: Layering patterns can silently cancel each other, especially for higher-level "stacked" effects.
- Suggested direction: Add explicit composition semantics (blend modes, priority, or intensity mixing), and document the default.

### F6. `seq()` hard-codes physical group names (Medium)
- Where: `src/dj_hue/patterns/strudel/core/pattern.py:101-143`
- Why it matters: `seq()` assumes `strip` and `lamps` are the "physical groups." This is a narrow assumption tied to one hardware setup.
- Impact on "lego" composition: Patterns written with `seq()` are less portable across installations.
- Suggested direction: Provide a configuration or metadata-driven mapping for "physical groups" in `LightContext`, not hard-coded names.

### F7. Envelope release is defined but not rendered (Medium)
- Where:
  - `src/dj_hue/patterns/strudel/core/envelope.py:86` (release phase)
  - `src/dj_hue/patterns/strudel/scheduler.py:155` (continues only through attack + decay)
- Why it matters: The ADSR model is documented, but release never influences rendering. This is confusing and limits expressivity for tails.
- Impact: Patterns that rely on release tails will not behave as expected.
- Suggested direction: Apply release when events end, or explicitly document that release is not supported.

### F8. Zone fallback remapping is a no-op (Low)
- Where: `src/dj_hue/patterns/strudel/spatial/combiner.py:64`
- Why it matters: Fallback patterns are not constrained to a specific zone even when only one zone exists. This undermines spatial fidelity in degraded setups.
- Impact: "Degraded" patterns can feel like a different pattern entirely.
- Suggested direction: Implement a wrapper that remaps `group == "all"` to a specified set of indices.

### F9. Mini-notation `/n` is documented but ignored (Low)
- Where: `src/dj_hue/patterns/strudel/dsl/parser.py:258`
- Why it matters: The notation claims to support "slow" but it is not implemented, so pattern authors can write expressions that silently do nothing.
- Impact: DSL inconsistencies reduce trust and create surprises.
- Suggested direction: Implement `/n` or remove it from docs.

### F10. Streaming implementation is duplicated (Low/Medium)
- Where:
  - `src/dj_hue/lights/streaming.py`
  - `src/dj_hue/cli/midi_pattern_mode.py`
  - `src/dj_hue/cli/midi_hue.py`
- Why it matters: Streaming code is duplicated with diverging behavior and group detection logic. This is a maintenance risk and can lead to subtle bugs across modes.
- Impact: Changes to streaming behavior will not propagate across all entry points.
- Suggested direction: Centralize streaming and group detection in one module, used by all CLIs.

## Strengths (Worth Preserving)

- Strudel's query-based pattern model is a great fit for deterministic, composable patterns.
- Immutable transforms and `LightHap`/`TimeSpan` make it easy to reason about time.
- Zone metadata (`PatternCapability`, `LayeredPattern`) is a clean abstraction for spatial setups.
- Hot-reload workflow enables fast pattern iteration and supports live performance needs.

## Recommendations (Practical Next Steps)

### Short Term (1-2 changes)
- Cache a scheduler for layered patterns so envelopes and modulators persist across frames.
- Fix time-unit mismatches by adding explicit conversion helpers and/or renaming APIs.
- Update `set_pattern_by_index()` to select Strudel and layered patterns.

### Medium Term (Structural)
- Define a single "renderable pattern" interface and adapt classic patterns into it.
- Add composition semantics for overlapping events (blend or priority).
- Parameterize `seq()` group behavior via `LightContext` metadata.

### Long Term (Lego-Like Composition)
- Use a single registry for all patterns with shared metadata, filtering, and selection.
- Build a "pattern graph" pipeline that transforms events and merges them in one place.
- Make zone remapping and fallback behavior explicit and testable.

## Open Questions

- Do you want explicit blending (additive, max, average) or strict priority when patterns overlap?
- Should the system support per-pattern timebases (beats per cycle) and mix them safely?
- Is "classic pattern" support intended to remain, or do you want to converge on Strudel?

## Closing

The core Strudel system is solid and is the right foundation for lego-style composition. The primary jank is in system integration and timebase consistency, not in the pattern DSL itself. If those seams are tightened, the system should scale to much more complex and versatile patterns.
