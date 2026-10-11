# 34 — 128×128 paired-BAT raycaster

**Example implementation. Not speed optimized, has issues.**

This is a demonstration of a 128×128, 16-colour *logical* raycaster on the PC Engine. Its physical display is 512×224, but the paired-BAT trick does not deliver 512 independently drawn horizontal pixels. Two 4-bit colour indices are encoded in each BAT word. The 256 static tile patterns live in VRAM, and the sky/floor backdrop is initialized once. Each frame updates **changed wall spans** within the BAT, not a whole software framebuffer.

The previous 128×64 atomic example was removed, including its build target, page-swap code and tests. The only maintained raycaster presentation is progressive 128×128. Reference shaders remain solely for same-resolution comparisons.

## Presentation path

The raycaster uses 128 ray directions, center-first paired-column ordering, a fixed 16-colour palette, close-range 32×32 wall texels, and lookup-driven wall shading. A sparse raster IRQ remaps 128 logical rows to 224 scanlines. The second half of the 128×64 **hardware BAT** is circularly shifted by one row to prevent a floor-coloured scanline at the midpoint boundary; this is not an alternate 128×64 image mode.

The staged uploader composes wall BAT words before VBlank, then transfers at most **138 BAT words per prepared batch**, in interrupt-masked bursts no larger than **eight words**. Unlike the historical uninterrupted 96-word upload, it **waits for raster IRQ progress between consecutive bursts**. That spreads writes into active scanlines while allowing BYR/RCR remapping to run between them. The VDC's auto-increment-by-128 remains active within physical BAT runs; only a segment change or the rotated BAT-page wrap requires a new MAWR address. Compile with `-DRAY_PRESENT_PACED=0 -DRAY_VBLANK_WORD_BUDGET=96` to restore the older presentation, or `-DRAY_PRESENT_CONTIGUOUS=0` to restore per-burst address setup.

**Important:** The 138-word setting is **emulator-tested, not a console-safe hardware specification**. A 144-word paced variant failed sustained movement (incomplete bitmap), while larger *unpaced* budgets produced missing raster interrupts. The upload bursts still briefly mask IRQs and can tear; the renderer is progressive rather than an atomic 128×128 display. Keep both the 540-frame consecutive-turn sweep and 1,080-frame movement stress as mandatory regression checks. Dirty-view commits are not full-screen FPS.

## Build and verify

With the LLVM-MOS PCE toolchain on `PATH`:

```sh
make                        # 128×128 ROM: build/34-rendered-raycaster.pce
make tables-check
PCE_HEADLESS=/path/to/pce-headless make column-regression
PCE_HEADLESS=/path/to/pce-headless make vram-pacing-compare
PCE_HEADLESS=/path/to/pce-headless make interaction-test
```

`make vram-pacing-compare` builds uninterrupted/96 and raster-paced/138 versions, checks exact stationary pixels, and records VRAM throughput and game-loop updates. `make vram-present-compare` instead compares the address-setup implementations *within the new pacing schedule*. `make column-benchmark` reports VRAM words, loop updates and completed dirty-view passes. `make raster-sweep` captures consecutive turning screenshots and checks for blank frames and the midpoint seam. `make bitmap-stress` tests sustained movement. The optional grid-traversal experiment remains opt-in (`-DRAY_GRID_CROSSING=1`), because earlier measurements showed a CPU-cycle reduction without convincing whole-image throughput improvement.

## Verified VRAM presentation comparison (emulator only)

`make vram-present-compare` runs the old per-burst address setup against the
contiguous-address implementation under identical controller scripts, followed
by an independent screenshot equivalence test. In the 1,080-video-frame
benchmark, **both** produce 14 changed-view passes, **1.500** turning
passes/second, and write **60,281 BAT words**. Their stationary screenshots
match over **135,520 RGB pixels**. The optimized path omits redundant VDC
MAWR register writes, but **has not demonstrated a whole-screen FPS increase**.
The 96-word contiguous build passed 540 consecutive rotation screenshots,
1,080 movement frames (19 completed dirty-view passes), and the native
profiler budget. A 104-word variant still failed sustained-movement tests;
this failed variant is not a release build.

## Verified paced presentation (emulator only)

The same 1,080-video-frame controller benchmark shows **77,017 BAT words**
transferred by raster-paced/136 in the *previous revision* versus **60,281** for uninterrupted/96, an
increase of about **27.8%**. Completed dirty-view passes rise **14 → 17**;
turning passes rise **1.500 → 1.833 per emulated second** (not full-screen FPS).
Game-loop updates are **1,056 → 1,051**. Their settled screens match exactly
across **135,520 RGB pixels**. On the separate 1,080-frame movement stress,
completed passes are **19 → 25** with no reported blank/partial raster; the
540-frame screenshot-by-screenshot turn sweep also passes the midpoint seam
check. Budget 144 failed the movement stress and is not the default. CPU
profiler gates pass. Input poses may diverge because the game loop can advance
a different number of updates: these rates are not equal-work raycaster
benchmarks, and actual PCE console behavior is unverified.

## X-indexed raster interrupt and bounded 138-word pacing

`gen_sparse_irq.py` now emits an X-only handler. It preserves X and A, but
no longer spills Y for each of the 127 scanline changes per frame. Loading,
incrementing, and saving `bat_source_y` through X also removes a memory
increment/read pair. Both variants retain the same ROM lookup tables and the
page-switch at logical row 64. Use `tools/gen_sparse_irq.py --legacy-output
build/bat_sparse_irq-legacy.S` to generate the old handler for direct
comparison; `make irq-compare` builds that handler with the old 136-word
pacing and checks the stationary image and dirty-view benchmark.

The equal-frames native profiler attributed **52,185** master-clock ticks per
frame to `irq_vdc` in the old handler and **47,592** in the X-indexed handler:
an **8.8% reduction in handler time**, not an 8.8% faster game. With a
138-word prepared batch (no more than eight words per masked burst), the
1,080-video-frame turning benchmark reached **2.000** dirty-view commits/sec
versus **1.833** for the previous release. The separate movement stress
completed **28** dirty-view passes versus **25** previously. The fast 138-word
variant also passed a **1,080-consecutive-frame** raster turn sweep with no
blank frames or midpoint-floor stripe. A 144-word variant failed the long
movement test; it is not enabled. These observations are emulator-only and
can change if CPU timing, scene state, or hardware behavior differs.

## Experimental natural-scroll IRQ (optional, not default)

`make natural-irq-rom` builds a *separate* 128×128 HuCard with
`src/bat_natural_irq.S`. This is an adaptation to the PCE's vertically uniform
bitmap tiles: setting the BYR offset near the end of a tile lets the VDC
advance naturally into the following logical row. Only **68 raster events**
are scheduled, versus **127** in the default X-indexed handler. The original
schedule is deliberately retained for logical rows 60–68, including the
rotated BAT page transition at 63/64, to prevent the midpoint stripe.
The generator is in `tools/gen_sparse_irq.py` and source-level tests verify
its entire event order and scroll offsets.

The experimental variant uses a **160-word prepared batch** and yields once
per two eight-word transfers, instead of the default 138 words with a yield
between each transfer. It is **not a hardware-safe transfer guarantee**:
140, 152 and 156-word experiments failed the 1,080-frame movement stress,
even though 144, 148 and 160 passed. The timing is sensitive to workload and
controller state; the production ROM remains unchanged. Use:

```sh
make natural-irq-rom
PCE_HEADLESS=/path/to/pce-headless make natural-irq-compare
PCE_HEADLESS=/path/to/pce-headless make natural-irq-stress
PCE_HEADLESS=/path/to/pce-headless make natural-irq-cycles
```

On the tested emulator, both ROMs match all **135,520 pixels** of the settled
frame. Over the 1,080-video-frame benchmark, turning dirty-view commits rise
from **2.000 to 2.167 per second**, and transferred BAT words from **77,895
to 88,115**. The separate movement stress completes **32** dirty passes,
versus **28** in the default ROM. The experimental ROM passes 1,080 consecutive
turning screenshot checks (including the midpoint) and 1,080 movement frames.
The native profiler attributes **47,592 -> 26,256** master-clock ticks
per video frame to `irq_vdc` (about **45% fewer**). The experimental cycle
budget retains the stable build's turn and walk constraints and tightens the
IRQ limit. It increases only the idle-`main` allowance because eliminating
interrupts shifts more frame-waiting time into the main-loop symbol; it does
not relax gameplay work budgets.

These are progressive dirty-view passes, *not full-screen video FPS*;
physical hardware remains untested.

## Limitations and references

This is educational source, not a production engine. FPS remains constrained by live BAT uploads and IRQ timing; the floor remains screen-anchored, 128×128 logical pixels look blocky, and emulator success is not physical-hardware certification.

The bitmap technique is based on [PCEdev's description](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/). The VCS-inspired coverage-span compositor and optional grid traversal are documented in `docs/vcs-port.md`, with the MIT-licensed reference sources retained. Older experimental variants remain in Git history for comparison, but are no longer build targets.
