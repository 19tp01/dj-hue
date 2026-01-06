# Strudel Pattern Test Results

Test Date: 2026-01-05
Test Setup: 6 lights (L0-L3 = strip, L4-L5 = lamps)
Legend: W=white, R=red, G=green, B=blue, .=black, lowercase=dim

---

## s_stagger
**Description:** Random sequential white flash, fades to red

**Expected:** At bar start, each light flashes white in random sequence on 16th notes, then fades to red. Each bar should have a different random order.

**Observed:**
- Beat 0: Only L1 and L5 flash (not all lights)
- Lights flash in pairs (L1+L5, L4, L0+L3, L2) - seems to be running per-group (strip and lamps separately)
- Fades to red as expected
- Random order changes each bar

**Issues:**
- Only 1-2 lights flash per beat, not a rapid sequence of all lights
- The `seq()` with `slots=16` should make each light get 1/16th of the bar, but it appears lights are being sequenced per-group with only ~4 lights in strip group getting 16 slots (lots of empty slots)

---

## s_beat_flash
**Description:** All lights flash on each beat

**Expected:** All lights flash white simultaneously on each beat, then fade to cyan.

**Observed:**
- All lights flash white on every beat (0, 1, 2, 3...)
- Color transitions W -> R -> G -> G through each beat
- No black dropouts (fixed!)

**Issues:**
- Fade color is cyan but showing as green (G) in test - may be RGB->char mapping issue, or actual color is greenish
- Otherwise works as expected

**Status:** PASS (minor color representation issue)

---

## s_downbeat
**Description:** Flash on beat 1 only

**Expected:** Flash white on beat 1 of each bar, fade to orange, rest of bar is ambient glow.

**Observed:**
- Beat 0: White flash
- Beats 0.25-1.75: Fades from R to r (getting dimmer)
- Beats 2-3.75: BLACK (no light)
- Beat 4: White flash again

**Issues:**
- Pattern uses `light("all ~*15")` which means "all" on beat 1, then rest (~) for 15 slots
- The rest slots are truly off (black), but description says "rest of bar is ambient glow"
- Sustain level drops to 0 because there's no sustain color/level set for the rest periods

**Status:** PARTIAL - Works as coded but description is misleading. If ambient glow is desired, pattern needs redesign.

---

## s_chase_smooth
**Description:** Lights chase smoothly around

**Expected:** Single light travels around all lights once per bar with smooth fade in/out.

**Observed:**
- Strip (L0-L3) and lamps (L4-L5) chase independently (per-group behavior)
- Beat 0: Black start (seems wrong)
- Smooth fade up/down on each light
- Chase completes once per bar

**Issues:**
- Beat 0 is black - the first light should be starting to illuminate
- Per-group behavior may or may not be desired (strip and lamps run separate chases)

**Status:** PARTIAL - Black at start of each bar

---

## s_chase_fast
**Description:** Quick chase, 4x per bar

**Expected:** Fast chase that cycles through all lights 4 times per bar.

**Observed:**
- Chase cycles correctly 4x per bar
- Strip and lamps run independently (per-group)
- Blue color as expected
- Each light is on for ~1 beat position at a time

**Issues:**
- None significant

**Status:** PASS

---

## s_chase_bounce
**Description:** Chase bounces back and forth

**Expected:** Chase that goes forward then backward through lights.

**Observed:**
- Beats 0-1.75: BLACK (nothing)
- Beats 2-3.75: Only L1 and L4 light up
- Pattern seems broken

**Issues:**
- Most of the bar is black
- `.rev()` is supposed to reverse but the pattern is nearly all black
- The seq().rev() combination doesn't seem to work as expected

**Status:** FAIL - Pattern is mostly black, bounce effect not visible

---

## s_strobe
**Description:** 16th note white strobe

**Expected:** On/off strobe at 16th note speed (16 flashes per bar).

**Observed:**
- Alternates ON/off every 16th note position
- 8 on-states + 8 off-states per bar = **8th note strobe, not 16th**

**Issues:**
- `light("all ~").fast(8)` creates 2 events × 8 = 16 events per bar
- 16 alternating events = 8 ON + 8 OFF = 8th note strobe
- For true 16th note strobe, need 32 events (16 ON + 16 OFF)
- Description is incorrect - this is 8th note strobe

**Status:** MISLABELED - Works as coded but is 8th note, not 16th note

---

## s_strobe_build
**Description:** Strobe speeds up over 8 bars

**Expected:** Strobe that starts slow and gets faster over 8 bars.

**Observed:**
- Bars 1-2: W for 2 beats, black for 2 beats (half note strobe)
- Pattern repeats identically each bar in our 2-bar test

**Issues:**
- Test only covers 2 bars, need 8 bars to see full build
- The first 2 bars should be quarter note strobe but showing as half-note (2 beats on, 2 beats off)
- May be timing/compression issue with `.slow(2)` interaction

**Status:** NEEDS LONGER TEST - 2-bar window insufficient

---

## s_gentle
**Description:** Slow ambient pulse

**Expected:** Slow 2-bar pulse, all lights together.

**Observed:**
- Beat 0: Black
- Beats 0.5-1.5: Dim red (r)
- Beats 1.75-2.5: Bright red (R)
- Beats 2.75-7.75: Dim red (r)
- Beat 8: Black

**Issues:**
- Peak occurs around beat 2, not centered
- Pulse is very subtle (mostly dim)
- Pattern takes 2 bars (.slow(2)) which is visible

**Status:** PASS - Works as designed, though could be more dramatic

---

## s_color_wash
**Description:** Slow color cycling across lights

**Expected:** Slow wave of color moving across lights over 2 bars.

**Observed:**
- Chase pattern (one light at a time) over 2 bars
- Strip and lamps run independently
- Red color, smooth fade
- Beat 0 and 8: Black

**Issues:**
- "Color cycling" suggests hue changes, but pattern is constant red
- Name is misleading - this is a slow chase, not a color wash

**Status:** PARTIAL - Works but name/description don't match behavior

---

## s_alternate
**Description:** Left/right alternating

**Expected:** Left side and right side alternate, perhaps each half bar.

**Observed:**
- Beats 0-1.75: Left (L0-L2) red, right black
- Beats 2-3.75: Left black, right (L3-L5) blue
- Alternates every 2 beats (half bar)

**Issues:**
- Works correctly but timing is half-bar, not quarter-bar
- Some might expect faster alternation

**Status:** PASS

---

## s_random_pop
**Description:** Random lights pop on each beat

**Expected:** Random light(s) flash on each beat.

**Observed:**
- 1-2 lights flash per beat position
- Random selection changes each beat
- Quick fade from white to yellow

**Issues:**
- Only 1-2 lights per beat, might expect more
- Randomness is working

**Status:** PASS

---

## s_green_cascade
**Description:** Neon green with sequential white flash at bar start

**Expected:** Even/odd lights alternate on quarter notes with green, white flash sequence at bar start.

**Observed:**
- Beat 0: W on even (L0, L2, L4), G on others
- Sequential flash visible in first beat (W->R->G transition on different lights)
- Even lights (0,2,4) and odd lights (1,3,5) alternate on quarter notes
- Green base color maintained

**Issues:**
- Flash seems to be only on even lights (L0, L2, L4), not all lights
- The interleaving of white flash and green pulse creates complex visual

**Status:** PARTIAL - Flash not covering all lights as expected

---

## s_blue_fade_strobe
**Description:** 2 beats bright blue fade, 2 beats blue strobe

**Expected:** First 2 beats: bright blue fading to 50%. Second 2 beats: blue strobe.

**Observed:**
- Beats 0-1: Bright blue (B), fades but stays fairly bright
- Beats 1.25-1.75: Dim blue (b)
- Beats 2-3.75: Alternating B and . (strobe)
- Pattern repeats in second bar

**Issues:**
- Fade section shows B then b - the 50% fade is visible
- Strobe section works as expected
- Overall structure is correct

**Status:** PASS

---

## Summary

| Pattern | Status | Notes |
|---------|--------|-------|
| s_stagger | PARTIAL | Not all lights sequencing, per-group issue |
| s_beat_flash | PASS | Works correctly |
| s_downbeat | PARTIAL | Works but no ambient glow as described |
| s_chase_smooth | PARTIAL | Black at bar start |
| s_chase_fast | PASS | Works correctly |
| s_chase_bounce | FAIL | Mostly black, bounce not working |
| s_strobe | MISLABELED | Is 8th note strobe, not 16th note |
| s_strobe_build | NEEDS VERIFY | Need 8-bar test |
| s_gentle | PASS | Subtle but works |
| s_color_wash | PARTIAL | Name misleading, is slow chase |
| s_alternate | PASS | Works correctly |
| s_random_pop | PASS | Works correctly |
| s_green_cascade | PARTIAL | Flash not on all lights |
| s_blue_fade_strobe | PASS | Works correctly |

### Priority Issues to Fix:
1. **s_chase_bounce** - BROKEN, mostly black
2. **s_stagger** - Not sequencing through all lights properly
3. **s_chase_smooth** - Black at bar start
4. **s_green_cascade** - Flash should be on all lights
5. **s_strobe** - Is 8th note, not 16th note as labeled

### Lower Priority:
6. s_downbeat - Needs ambient glow during rest (or update description)
7. s_color_wash - Rename or add color cycling
