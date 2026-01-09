#!/usr/bin/env python3
"""Test script to log frames for basic strobe pattern - shows what each light receives at each batch."""

from fractions import Fraction
from dj_hue.patterns.strudel import light
from dj_hue.patterns.strudel.core.types import TimeSpan, LightContext
from dj_hue.patterns.strudel.scheduler import PatternScheduler

# Create a simple context with 6 lights
context = LightContext(
    num_lights=6,
    groups={
        "all": list(range(6)),
        "strip": [0, 1, 2, 3],
        "lamps": [4, 5],
    }
)

# The pattern to test
pattern = light("all ~").fast(16)

print("=== Testing: light('all ~').fast(16) ===\n")

# Show the pattern structure
print("--- Pattern structure ---")
print(f"Base 'all ~': on [0, 0.5], rest [0.5, 1.0]")
print(f"fast(16): compress and repeat 16x per cycle")
print(f"Expected: 16 flashes per cycle, each 1/32 cycle duration\n")

# Create scheduler (like the real render loop does)
scheduler = PatternScheduler(pattern, context, cycle_beats=4.0)

# Simulate at 50Hz for one cycle (4 beats @ 120 BPM = 2 seconds = 100 frames)
frames_per_cycle = 100
cycle_beats = 4.0

print("--- Frame-by-frame batch output (50Hz, 1 cycle) ---")
print("Format: Frame | Beat | Light0 | Light1 | Light2 | Light3 | Light4 | Light5")
print("-" * 80)

def rgb_to_bar(rgb) -> str:
    """Convert RGB to a visual indicator."""
    brightness = (rgb.r + rgb.g + rgb.b) / (3 * 255)
    if brightness > 0.5:
        return f"ON  ({rgb.r:3d},{rgb.g:3d},{rgb.b:3d})"
    elif brightness > 0:
        return f"dim ({rgb.r:3d},{rgb.g:3d},{rgb.b:3d})"
    else:
        return "OFF (  0,  0,  0)"

# Track state changes for summary
prev_colors = None
state_changes = []

for frame in range(frames_per_cycle):
    # Convert frame to beat position (0-4 beats per cycle)
    beat_position = (frame / frames_per_cycle) * cycle_beats

    # This is exactly what the render loop does
    colors = scheduler.compute_colors(beat_position)

    # Check if state changed
    current_state = tuple((c.r, c.g, c.b) for c in [colors[i] for i in range(6)])
    if prev_colors != current_state:
        state_changes.append((frame, beat_position, colors))
        prev_colors = current_state

        # Print this frame
        light_states = " | ".join([
            f"{'ON ' if colors[i].r > 0 or colors[i].g > 0 or colors[i].b > 0 else 'OFF'}"
            for i in range(6)
        ])
        print(f"Frame {frame:3d} | Beat {beat_position:5.3f} | {light_states}")

print("-" * 80)
print(f"\nTotal state changes: {len(state_changes)}")
print(f"Expected: 32 changes (16 on→off pairs for a 16x strobe)")

# Show detailed RGB values for first few changes
print("\n--- First 10 state changes (detailed RGB) ---")
for i, (frame, beat, colors) in enumerate(state_changes[:10]):
    print(f"\nFrame {frame} (beat {beat:.4f}):")
    for light_id in range(6):
        rgb = colors[light_id]
        print(f"  Light {light_id}: R={rgb.r:3d} G={rgb.g:3d} B={rgb.b:3d}")

# Analysis
print("\n--- Timing Analysis ---")
if len(state_changes) >= 2:
    on_durations = []
    off_durations = []
    for i in range(0, len(state_changes) - 1, 2):
        if i + 1 < len(state_changes):
            on_frame, on_beat, _ = state_changes[i]
            off_frame, off_beat, _ = state_changes[i + 1]
            on_durations.append(off_frame - on_frame)
        if i + 2 < len(state_changes):
            off_frame, off_beat, _ = state_changes[i + 1]
            next_on_frame, next_on_beat, _ = state_changes[i + 2]
            off_durations.append(next_on_frame - off_frame)

    if on_durations:
        print(f"Average ON duration: {sum(on_durations)/len(on_durations):.1f} frames")
    if off_durations:
        print(f"Average OFF duration: {sum(off_durations)/len(off_durations):.1f} frames")

    print(f"\nAt 50Hz, 1 frame = 20ms")
    print(f"Expected: ~3.1 frames ON, ~3.1 frames OFF (for 50% duty cycle)")
