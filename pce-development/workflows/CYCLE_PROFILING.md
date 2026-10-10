# Measured HuC6280 master-clock profiling

This extends `perf_pair.py` (which counts executed instructions) with the
**actual CPU timestamp deltas** from the Mednafen-derived PCE core. The
headless RPC already supports `prof_start` / `prof_dump`; no ROM debugger
hooks or CPU-cycle approximations are needed. Use the RPC-capable rebuilt
headless emulator, not the older prebuilt binary which lacks these calls.

## Commands

```sh
PCE_HEADLESS=/path/to/pce-headless make cycles-ray
PCE_HEADLESS=/path/to/pce-headless make cycles-all
python3 pce-development/workflows/cycle_profile.py gate \
  --report build/cycles/raycaster/report.json \
  --budget pce-development/workflows/specs/cycles/raycaster-budget.json
# To compare separately built local ROMs with identical scenarios:
python3 pce-development/workflows/cycle_profile.py compare \
  --baseline old/report.json --optimized new/report.json --out comparison.json
```

For each segment, the tool warms up the ROM, installs a controller mask,
starts profiling, runs exactly the specified number of emulator VBlanks,
and dumps a *physical-address* cycle histogram. The `.mlb` attributes ROM
bytes to their linked function names (including banked ROMs); non-ROM
addresses are listed as unmapped rather than silently called application
code. Inlining contributes costs to the containing routine; no call graph
is available. The profiler counts elapsed **master clock ticks**, not one
CPU instruction per tick, not nominal 7.16 MHz cycles, and not wall-time FPS.
VDC steals, interrupts and waiting are included in the histogram.

**Profiler validation:** Each 60-frame NTSC window should be near
357,600 master ticks/frame in the emulator. Any out-of-band total is
rejected instead of producing a plausible-looking report. The optional
`progress` spec checks an actual main-RAM frame counter (platformer) or
G2TR's two complete records (raycaster/racer); it rejects a stalled game
and reports *completed game updates per emulator frame*. This matters
because a 60 Hz video output need not run a complex raycaster at 60 Hz.

**Comparability:** Only compare equivalent input scripts, frame counts,
executed game updates and initial scene state. If the completed update
counts differ, `compare` suppresses per-symbol speedup estimates. Even
matching update counts cannot establish identical game state or identical
hot-loop work. A source refactor that splits a function changes its
symbol mapping; direct before/after `main` costs would be misleading.
Use per-routine budgets to guard a *fixed build* against regressions.

**Measured bottlenecks and interpretation:** On the tested local headless
build, the textured 512x224 raycaster spent about 197,893 master ticks per
video frame in `irq_vdc` when idle (55.3% of the ~357,608-tick NTSC frame
budget). On rightward rotation that grows to roughly 219,656 ticks/frame
(61.4%). Its bitmap work is reported under `main` (the inlined slice writer),
`wall_pixel` and `cast_scene`. The latter two have independent symbols;
the slice writer remains intentionally part of `main`. During 60 emulator frames, the updated raycaster completed 15
updates while idle and 10 while turning. As one complete 128-row image takes
32 four-row updates, this is approximately 128 and 192 video frames per
full redraw, respectively, **assuming a comparable sustained workload**.
This is an estimate from real game-state progress, not a measured stable
full-redraw FPS or physical hardware timing. It also reveals why a mere
emulator video-frame counter fails to prove a fast renderer.

The faster floor-plane scale cases and fixed tile-mask generation no longer
pull the `__ashlhi3` software shift helper into the raycaster ELF. The
512x224 tiled-pair pseudo-bitmap, image quality and hardware display mapping
are preserved. The optimized slice writer stays inlined: forcing it out of line
caused intermittent incomplete raster captures in a 480-frame acceptance run.
That variant was rejected rather than masking the visual regression. The removal is compiler-symbol verified, but the new function
boundaries prevent treating a change in `main`'s attributed cycles as an
end-to-end speedup. The raster IRQ itself is the next architectural
optimization target. For the platformer, `p4_tick` is now a separately
attributed routine and its measured per-frame cost differs between idle,
walking and jumping.

## How AI agents should use the reports

1. Start with `make cycles-ray` and inspect `report.md`'s top routines and
   `report.json`'s `game_updates` and `updates_per_emulator_frame`.
2. Optimize an identified named hot path rather than an arbitrary C line.
3. Preserve the existing screenshot/collision scenarios and ROM arithmetic
   link checks. Re-profile the same scene and inputs.
4. Reject missed game updates, stale captures, invalid profiler files,
   unlabelled execution or regressions in the explicit budgets.
5. Say **emulator master-clock ticks**, not measured console cycles, FPS or
   guaranteed gameplay speedup. Only independently timed hardware can
   establish hardware-specific performance.

Offline negative tests for malformed profiles, fake frame totals, overlapping
symbol names, incomplete G2TR publication, invalid scenarios, regression
budgets and inequivalent comparisons are in `tests/test_cycle_profile.py`.
No internet access, package installation, LLM calls or private transcripts
are involved.
