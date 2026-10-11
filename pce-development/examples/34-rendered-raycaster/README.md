# 34 — 128×128 paired-BAT raycaster

**Example implementation. Not speed optimized, has issues.**

This is a demonstration of a 128×128, 16-colour *logical* raycaster on the PC Engine. Its physical display is 512×224, but the paired-BAT trick does not deliver 512 independently drawn horizontal pixels. Two 4-bit colour indices are encoded in each BAT word. The 256 static tile patterns live in VRAM, and the sky/floor backdrop is initialized once. Each frame updates **changed wall spans** within the BAT, not a whole software framebuffer.

The previous 128×64 atomic example was removed, including its build target, page-swap code and tests. The only production raycaster presentation is progressive 128×128. An optional VRAM-buffered experiment is documented below; reference shaders remain solely for same-resolution comparisons.

## Presentation path

The raycaster uses 128 ray directions, center-first paired-column ordering, a fixed 16-colour palette, close-range 32×32 wall texels, and lookup-driven wall shading. A sparse raster IRQ remaps 128 logical rows to 224 scanlines. The second half of the 128×64 **hardware BAT** is circularly shifted by one row to prevent a floor-coloured scanline at the midpoint boundary; this is not an alternate 128×64 image mode.

The staged uploader composes wall BAT words before VBlank, then transfers at most **138 BAT words per prepared batch**, in interrupt-masked bursts no larger than **eight words**. Unlike the historical uninterrupted 96-word upload, it **waits for raster IRQ progress between consecutive bursts**. That spreads writes into active scanlines while allowing BYR/RCR remapping to run between them. The VDC's auto-increment-by-128 remains active within physical BAT runs; only a segment change or the rotated BAT-page wrap requires a new MAWR address. Compile with `-DRAY_PRESENT_PACED=0 -DRAY_VBLANK_WORD_BUDGET=96` to restore the older presentation, or `-DRAY_PRESENT_CONTIGUOUS=0` to restore per-burst address setup.

**Important:** The 138-word setting is **emulator-tested, not a console-safe hardware specification**. A 144-word paced variant failed sustained movement (incomplete bitmap), while larger *unpaced* budgets produced missing raster interrupts. The upload bursts still briefly mask IRQs and can tear; the renderer is progressive rather than an atomic 128×128 display. Keep both the 540-frame consecutive-turn sweep and 1,080-frame movement stress as mandatory regression checks. Dirty-view commits are not full-screen FPS.

## Optional VRAM-backed 128×128 image buffer (experimental)

The article [PCE bitmap mode](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/)
describes the tilemap acting as a bitmap in **VRAM**, and discusses using
VDC VRAM-to-VRAM DMA for clearing/copying. It does **not** provide an instant
second BAT-base register. The VDC has only a single visible BAT at `$0000`.
This 128×128 representation fills its 8,192 words (a 128×64 hardware BAT).
Increasing the HuCard ROM allowance to **1 MiB** does not enlarge the PCE's
64 KiB video RAM, nor provide a second display base or faster VRAM access.

A deliberately **opt-in** implementation composes a complete updated
128×128 image into the free 8,192-word VRAM region `$4000..$5FFF`, keeping
patterns at `$2000..$2FFF` and the visible BAT at `$0000..$1FFF` untouched
while rendering. Once complete, it copies the image back into the visible BAT
with two VDC-to-VRAM DMA transfers of **4,096 words each**. The LLVM-MOS
`pce_vdc_dma_start()` *implementation* passes `length - 1` straight to the
hardware word-count register (despite the byte-length wording in its API
documentation), so the units must be **words**. An unsegmented 8,192-word
copy failed the pixel-equivalence test; these two bounded copies passed.

**Caution:** these are two distinct display updates across VBlanks; this is
real offscreen buffering but **not an atomic double-buffer page flip**.
It can show a mixture of successive views during the DMA copy, and it has
not demonstrated higher FPS than the stable reduced-IRQ variant. Keep the
progressive renderer as the default. On the tested emulator the opt-in mode
made **2.333 completed DMA presentations/sec** during turning, versus
**2.000 progressive dirty-view commits/sec** for the default renderer in the
same 1,080-video-frame scenario. A separate reduced-IRQ progressive ROM
previously achieved 2.167 dirty-view commits/sec.
These are different kinds of completion and are **not** directly comparable
FPS. The buffered experiment also requires 8,192 DMA-copy words **per
presentation** in addition to the offscreen word writes. It passed exact
settled-image equivalence (0 / 135,520 differing physical pixels), 1,080
consecutive turn screenshots, 1,080 frames of movement stress, and the
interaction trace; none of those tests proves atomic presentation.

```sh
make vram-buffer-rom
PCE_HEADLESS=/path/to/pce-headless make vram-buffer-compare
PCE_HEADLESS=/path/to/pce-headless make vram-buffer-stress
```

### DMA completion interrupt experiment (not an atomic flip)

`make vram-buffer-irq-rom` builds another opt-in 128×128 buffered version.
Its raster IRQ handler signals DMA completion *after* the scanline scroll
registers are written. This avoids repeatedly reading the VDC status register
while the main loop waits for DMA: each status read can acknowledge raster
interrupts, interfering with the bitmap-row remapper. The experiment uses two
4,096-word copies **back-to-back** after a video-frame boundary, rather than
waiting another VBlank between copies. It still has no physical page flip and
**cannot promise a tear-free presentation on actual hardware**.

In the 1,080-video-frame emulator benchmark, the earlier polling implementation
measured **2.333 completed presentations/sec while turning**; the interrupt
version measured **2.167**. Both made 18 total commits in that scenario.
The new path does **not** demonstrate an FPS improvement. Its stationary image
matches the progressive reference exactly; the 540-frame raster sweep and
1,080-frame movement stress also passed. Tests of one 8,192-word DMA and
8×1,024-word dirty-stripe DMAs were rejected due to image mismatch or
raster stalls. Increasing the staged word budget beyond 192 was also slower or
unstable. Keep the polling version and progressive default available.

```sh
PCE_HEADLESS=/path/to/pce-headless make vram-buffer-irq-compare
PCE_HEADLESS=/path/to/pce-headless make vram-buffer-irq-stress
```

The `vram-buffer-compare` target requires **exact** independent emulator
screenshots before publishing performance numbers, preventing the earlier
DMA overrun/corruption from being mistaken for a speedup. Both presentation
modes remain subject to raster and movement stress tests. Hardware timing
has not been validated; a guaranteed tear-free 128×128 swap on a base PCE
would require a different representation or additional video hardware.

## Optional compressed-tile VBlank page flip (experimental)

`make tiled-pageflip-rom` builds an **actual VBlank-selected pair of 128×128
logical images** without the two visible DMA copies. This is a separate,
**lossy** rendering format and does **not** replace the default 16-colour
paired-BAT renderer. It remains an example implementation, not speed
optimized, and has issues.

The VDC's 128×64 BAT still occupies 8,192 VRAM words. Each offscreen/onscreen
page instead uses only **2,048 words**: 64 BAT columns × 32 BAT rows. These
fit side-by-side in the same BAT (columns 0–63 for page A, columns 64–127
for page B). An 8-bit glyph index stores a 2×4 mask of logical pixels,
with *two selected colours per tile*. The fixed 256-pattern atlas occupies
VRAM `$2000..$2FFF`. Sixteen palette pairs approximate the source's original
16-color texels, with a visible reduction in texture and shade fidelity.
Each logical pixel occupies four physical display pixels horizontally and
one or two vertically. The VDC naturally advances its vertical scroll and
needs only **31 active raster row-skip updates**, rather than the default
127; a VBlank IRQ changes BXR between 0 and 512 only after the entire
hidden BAT page is filled. This is a true *compressed-page flip*, not a
second BAT-base register or full-color bitmap double buffering.

The mode initially updates four columns' worth of BAT tile groups per
rendering iteration (128 words). On the emulator's 1,080-video-frame
benchmark it measured **1.0 complete VBlank page flip/second while turning**;
by contrast the unchanged 16-colour progressive renderer measures about
**2.0 dirty-view commits/second** and the earlier IRQ-buffered DMA renderer
about **2.167 completed-copy presentations/second**. Those operations are
not equivalent FPS measures. The experiment is **slower and more posterized**
than the previous default; the benefit is a genuine VBlank page selection
with no full-frame VRAM copy. Although up to 1 MiB of ROM is permitted, this
prototype uses a 32-KiB HuCard and does not yet exploit larger precomputed
compression tables.

The opt-in regression verifies that the image remains unchanged across
screenshots sufficiently far from any VBlank flip, allowing for the emulator's
one-frame lag between screenshot capture and CPU-state reads. In a **1,080
consecutive-turn-frame** run, this and the pixel-diversity/midpoint checks
passed. A separate **1,080-frame six-part movement test** passed. These are
emulator validations, **not** hardware timing certification. The image is
not pixel-equivalent to the 16-color source and should not be substituted
for it in image-equality gates.

```sh
make tiled-pageflip-rom
PCE_HEADLESS=/path/to/pce-headless make tiled-pageflip-verify
```

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
between each transfer. Pacing re-arms after each video-frame rollover instead
of comparing later waits against the batch's first frame: long transfers now
continue to wait for raster progress even after crossing VBlank. It is **not a hardware-safe transfer guarantee**:
140, 152 and 156-word experiments failed the 1,080-frame movement stress,
even though 144, 148 and 160 passed. The timing is sensitive to workload and
controller state; the production ROM remains unchanged. Use:

```sh
make natural-irq-rom
PCE_HEADLESS=/path/to/pce-headless make natural-irq-compare
PCE_HEADLESS=/path/to/pce-headless make natural-irq-stress
PCE_HEADLESS=/path/to/pce-headless make natural-irq-marathon
PCE_HEADLESS=/path/to/pce-headless make natural-irq-cycles
```

On the tested emulator, both ROMs match all **135,520 pixels** of the settled
frame. Over the 1,080-video-frame benchmark, turning dirty-view commits rise
from **2.000 to 2.167 per second**, and transferred BAT words from **77,895
to 88,115**. The separate movement stress completes **32** dirty passes,
versus **28** in the default ROM. The experimental ROM passes 2,160 consecutive turning screenshots (including
the midpoint), 1,080 movement-stress frames, and a separate 4,320-frame
mixed-input marathon with 24 screenshot checkpoints. The marathon explicitly
allows a genuine near-wall (depth 1–2) view to occupy the sky/floor: the older
six-checkpoint palette-diversity rule falsely diagnosed those close walls as
missing graphics. It still rejects empty frames, midpoint stripes and stalls.
A 160-word budget remains experimental: neither these tests nor an emulator
provide physical-hardware raster-timing proof.
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

### ROM lookup acceleration for compressed VBlank page flips

The compressed-page experiment optionally uses `RAY_TILE_FAST_QUANT=1`
(the default for that **experimental** ROM only). Two generated tables indexed by
one packed source-pixel pair provide palette error and two glyph-pattern bits.
They replace eight per-pixel palette tests and bit shifts per tile, while
preserving the legacy renderer's 8-bit score wrap exactly. The two tables
occupy 8 KiB of **ROM**, not PCE VRAM; the resulting HuCard still fits in
32 KiB despite the permitted 1 MiB ceiling. The standard 16-colour renderer
and the older VRAM-buffered/DMA renderers are unchanged.

For a same-source comparison, run:

```sh
PCE_HEADLESS=/path/to/pce-headless make tiled-pageflip-speed-compare
PCE_HEADLESS=/path/to/pce-headless make tiled-pageflip-verify
```

In the 1,080-frame emulator benchmark, the older compressed tile converter
achieved **1.000 complete VBlank flips/sec while turning** (12 total flips)
versus **1.333** (14 total flips) with the ROM lookups. A stationary capture
matched **exactly, 0 / 135,520 physical pixels differing**. The new tiled
renderer passed 2,160 consecutive turning screenshots (54 actual flips) and
1,080 frames of mixed movement. Four 32-word groups per game update provided
better game-loop responsiveness than eight; two groups were slower to complete
whole image pages. The displayed artwork remains a deliberately **lossy
2-colour-per-tile approximation**, not the original 16-colour image. It is not
an unqualified FPS comparison against progressive dirty-view commits or DMA
completion counts. No physical PCE validation has been performed.
