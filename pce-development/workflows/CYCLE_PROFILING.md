# Measured HuC6280 master-clock profiling

This extends `perf_pair.py` (which counts executed instructions) with the
**actual CPU timestamp deltas** from the Mednafen-derived PCE core. The
vendored headless RPC implements `prof_start` / `prof_dump`; no ROM debugger
hooks or CPU-cycle approximations are needed. Build the emulator from the
vendored source to avoid accidentally profiling with an older external binary.

The native profile clock now explicitly flushes the pending instruction at each
video-frame timestamp reset and retains the physical PC when a block transfer
runs across multiple frames. Starting a fresh RPC segment discards the prior
clock anchor. The frontend rejects failed `prof_dump` writes, reports the
number of exported addresses and total master ticks, and rejects dumps without
an active capture. The Python reporting tool checks these native totals against
the saved histogram before attributing cycles. These are committed changes under `third_party/`, not just
Python-side report logic. `make cycles-check` also compiles and executes a
small C++ regression test of this real native helper.

## Commands

```sh
make headless-build  # builds vendored source; requires Mednafen build deps
make cycles-check    # offline tests, including native profiler clock
make headless-profiler-smoke  # needs the built emulator + LLVM-MOS SDK
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

## Native 512x224 bitmap raster IRQ (2026-10-10)

The Mode 7 lesson and rendered raycaster now opt into a shared HuC6280
`irq_vdc` written with ST0/ST1/ST2, eliminating the compiler's extensive
interrupt prologue, pointer writes and redundant BXR updates. Source:
`pce-development/libcommon/src/bat_bitmap_irq.S`, vendored identically in
the standalone raycaster as `src/bat_bitmap_irq.S`.

**Measured per 60 emulated video frames, identical input masks and warmup:**

| ROM / segment | C raster IRQ ticks / video frame | native IRQ ticks / video frame |
|---|---:|---:|
| Raycaster idle | 197,893 | 83,248 |
| Raycaster turn right | 219,656 | 96,593 |
| Raycaster walk forward | 206,598 | 87,696 |
| Mode 7 idle | 263,181 | 134,407 |
| Mode 7 turn | 114,060 | 58,249 |
| Mode 7 forward | 114,060 | 58,249 |

These are *emulated master ticks attributed to the IRQ*, **not** game-update
CPU cost or a direct 60 Hz frame-rate claim. Raycaster updates per 60
emulator frames changed from 15/10/13 (C) to 23/17/21 (native IRQ), so the
profiler correctly marks per-routine run-to-run speedup comparisons as
**non-equivalent work**. The IRQ itself is materially cheaper in both
scenarios; further improvements need equal-work benchmarks and hardware
confirmation. Mode 7 redraws with the display paused, so the IRQ is active
for different proportions of each segment.

**Important profiler trap:** LLVM-MOS will export an assembly `irq_vdc`
as a singleton physical address unless both `.type irq_vdc,@function` and
`.size irq_vdc, .-irq_vdc` are supplied. The profiler used to charge most
of those cycles to `<unmapped>`, implying a false ~99% savings. `rom_labels`
now rejects that incomplete map and the raycaster budgets require >=99%
ROM attribution. Never benchmark from an incomplete symbol map.

**Rejected experiment:** scheduling raster IRQs only on logical-pixel row
transitions reduced cycle cost but caused long-held VRAM writes to miss the
first comparator and intermittently show a sky-only screen during rotation.
The working native handler retains the known-good per-physical-scanline
schedule, and is checked with both long-duration screenshots and G2TR
collision scenarios.

The native ISR's BYR high byte must borrow at **each multiple of 32**
logical rows: `((y & 63) << 3) - 1` has a borrow for `y` of 0, 32, 64,
and 96. A prior assembly attempt borrowed only when `y & 63 == 0`,
which created two dark lines in the Mode 7 sky. The micro screenshot smoke
and `test_native_bitmap_irq.py` now catch this regression.

## BAT redraw throughput and the TIA attribution caveat

The 512x224 raycaster's eight-row VBlank `TIA` upload was benchmarked against
an independently compiled **four-row TIA** configuration of the exact same
instrumented C source. The test counts `ray_redraws` after every fully
transferred 128-row BAT pass, not before a rendering iteration. In six
180-frame emulator segments (idle, two right turns, forward, left, idle),
**10 vs 16** completed passes were measured, a 60% improvement in completed
redraws per fixed emulator interval. Screenshots in all six segments were
validated independently for wall/floor geometry, and the turning screenshots
have different pixel content. Use `make raycaster-throughput`.

The 8-row version has a higher raster IRQ tick count per *video frame* than
the old 4-row C uploader, while its *completed redraw* throughput improves.
This is not evidence that its IRQ code slowed down: the TIA upload changes
interrupt-masking and scheduling, and both variants complete different work.
Only comparable full-image throughput is claimed here.

LLVM-MOS's shipped `pce_memop` assembly has a singleton `.mlb` symbol. The
linker's `.pce.map` specifies the exact `.text.pce_memop` section extent;
`cycle_profile.py` now uses that *verified* section size instead of guessing
where SDK code ends. The Mednafen core still records some block-transfer
ticks at synthetic non-ROM PCs (e.g. `$1F0003`), which cannot honestly be
charged to a ROM function. The revised `raycaster-budget.json` requires >=98%
attribution and caps these **unmapped master-clock ticks per frame** rather
than inventing a per-function cycle saving. Do not equate missing attribution
with free CPU time.
