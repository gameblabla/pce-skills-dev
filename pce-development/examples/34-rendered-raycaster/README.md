# 34 — textured bitmap raycaster (512x224 PCE mode)

Real Wolf3D-style raycasting, drawn through the **same paired-BAT bitmap
backend as the Mode 7 example** (`src/bat_bitmap.h`, kept in this exported
project). It sets 512x224 video and exposes a 128x128 logical 16-colour
framebuffer made out of BAT words, not per-frame planar graphics uploads.
Each BAT word stores two four-bit pixel indices in a fixed 256-pattern set.

32 signed fixed-step rays hit an 8x8 wall map. Rendering writes textured
stone/brick/metal walls, distance-varying wall heights, a ceiling gradient,
and a perspective checker floor **pixel by pixel into the BAT**. LEFT/RIGHT
turn and UP/DOWN move, sliding against solid walls. No sound or fonts.

`tools/gen_ray_tables.py` generates Q8 ray steps, wall heights and vertical
texture coordinates offline, avoiding runtime division/multiplication.
Regenerate with `python3 tools/gen_ray_tables.py`; `make tables-check` rejects
stale tables. `make`, `make trace`, `make visual-test`, and
`make interaction-test` exercise compilation, state and collision, and
independent rendered-pixel changes.

The bitmap uses `src/bat_bitmap_irq.S`, an interrupt-safe native HuC6280
handler with direct ST0/ST1/ST2 register writes. It replaces the costly C
ISR; `libcommon/src/bat_bitmap_irq.S` is the same implementation for Mode 7.
The handler preserves CPU registers and owns only VDC raster registers.
Its `.type`/`.size` declarations are essential for accurate ROM cycle maps.

A *working textured starter*, not a 60 FPS Wolf3D engine: the renderer
stages **eight logical rows per game update** in 1024 bytes of work RAM,
then uploads them using eight bounded HuC6280 `TIA` transfers to the two
alternating VDC data ports (`$0002/$0003`) during VBlank. The BAT, rather
than RAM, remains the framebuffer. A complete 128-row pass now spans
**16 updates** rather than 32. The game caches the floor's camera origin
for the entire pass instead of mixing camera coordinates halfway through.

HuC6280 `TIA` stalls interrupts for the duration of each transfer, so the
size of the batch and the VBlank timing matter. The naïve **eight-row C-loop
upload failed the emulator bitmap test** and was rejected; a sparse raster
IRQ schedule also intermittently showed sky-only frames. This implementation
keeps the native per-scanline IRQ and commits only during VBlank. The
`bitmap-stress` test checks six real screenshots and counts full BAT passes.
Do not increase to 16 rows without independent raster timing validation.

Over an identical **1,080-emulated-frame** input script, two instrumented
variants of this same source completed **10** full redraws with four rows
per `TIA` update and **16** with eight rows: **60% more completed BAT passes**.
These are actual ROM-owned post-VRAM-commit counters, not estimates from
G2TR game-update counts. Game-update counts differ (347 vs 263), so per-game-
update instruction savings cannot be inferred. Progressive BAT writes are
not atomic fullscreen swaps and physical-hardware timing is unverified.
`make visual-test`, `make bitmap-test`, `make bitmap-stress`,
`make bitmap-throughput` and `make interaction-test` test the different risks.

Measured emulator master-clock raster-IRQ savings are documented in
`../../workflows/CYCLE_PROFILING.md`; they do not establish hardware FPS.

## Independent visual check

`make bitmap-test` runs the actual ROM for 180 emulator frames and checks
for distinct ceiling, wall and floor colours, visibly textured wall regions,
and absence of the cyan palette holes seen in earlier Mode 7 prototypes.
The game emits G2TR telemetry separately: wall collision tests validate
actual map movement. The renderer's BAT writes are sliced across 16 game
updates, so a complete new viewpoint is progressive rather than instant.

## Completed redraw benchmark

```sh
PCE_HEADLESS=/path/to/rpc-capable/pce-headless make bitmap-throughput
```

This builds the same C source in two configurations: four rows/update and
eight rows/update, both with TIA uploads. It runs the **same six 180-frame
controller segments** on both ROMs, checks the actual emulator pixels at
every capture (allowing either grey metal or warm brick textures), rejects
stalled game loops and incomplete BAT passes, and compares the RAM counter
`ray_redraws`, incremented only after the last BAT row reaches VDC VRAM.
Results and emulator PNGs are under `build/bitmap-{baseline,optimized}*`.
`tools/bitmap_compare.py` refuses different controller scripts and incomplete
visual evidence. Neither a passing compile nor G2TR-only state is accepted.

## Faster full-detail texture sampling (no resolution loss)

**This change optimizes only the shader, not the BAT layout or image geometry.**
`tools/gen_wall_pairs.py` produces the checked 640-byte `src/wall_pairs.h`
lookup: five pre-shaded stone/brick/metal material classes, 8 horizontal
texture phases and 16 vertical texture phases. One table fetch returns **two
independent 4-bit pixels packed into a BAT byte**. Material and distance fade
classes are selected once per 32-ray cast (`wall_style[]`), rather than taking
branches and evaluating the wall shader twice for each BAT pair.
All runtime table strides are powers of two; no target-side multiply/divide.
The colour palette, 128x128 bitmap and 8-row VBlank TIA uploads are unchanged.

`make wall-lookup-check` compares **24,576** material/depth/face/texture-phase
cases against the original shader; `make wall-lookup-visual` compares every RGB
pixel from two independently emulated 600-frame idle screenshots. Both must
pass, not merely look similar. `make wall-lookup-throughput` compares two
**same-resolution, same-upload** ROMs using six input-driven captures and
real completed-BAT-pass counters. The reference build uses
`-DRAY_WALL_LOOKUP=0` (old conditional shader); the optimized full-detail ROM
uses the generated lookup by default.

In the recorded 1,080-emulator-frame run, the original conditional shader
completed 16 full 128x128 redraws (263 game updates); the generated-pair shader
completed **19** (304 game updates), **18.75% more completed image passes**.
The stationary full-detail emulator screenshots were pixel-for-pixel identical
across 135,520 RGB screenshot pixels. LLVM-MOS C function boundaries/inlining
change between versions, so do not claim a comparable per-function cycle
saving. The profiler reports are emulator master ticks, **not console timing**.

The optional atomic version is still a **separate** 128x64 double-BAT-page
binary (`make atomic-rom`), with its own `atomic-test` and `atomic-stress`.
It shares the cheap shader but **does not become the default**, and its
completed page flips must never be compared to full-detail redraw counts as
if they were equally detailed images. A future *symmetric* top/bottom
raycaster might deliberately mirror 64 unique rows to make this compromise
more attractive; this project does **not** claim to implement that mirrored
raster mapping, nor that its current ceiling and floor are symmetric.

## Alternate atomic presentation: trade vertical detail for two VRAM BAT pages

**Default (`make`)** remains the original **128x128 logical pixels**, which
fills all 8,192 BAT words: no second full-resolution BAT page exists. This is
why the default displays gradual row writes, even with eight-row TIA updates.

To **eliminate partial-page updates from the displayed image**, build a
separate **128x64 logical pixel** variant with `make atomic-rom`. The physical
VDC mode is still 512x224, but each logical row is vertically magnified
3–4 scanlines. It divides the 128x64 BAT into two disjoint 64x64-word
half-pages: display the current half with BXR=0 or BXR=512, render all 64 rows
into the other half with eight bounded TIA slices, then flip BXR **only in the
VBlank IRQ** after the last row has been uploaded. The IRQ owns the page
handoff; the game never writes the visible page.

`make atomic-bitmap-test` checks actual emulator screenshots and ROM-owned
swap/page counters at 4-frame intervals, including a bounded screenshot
capture latency. `make atomic-stress` performs the complete 1,080-frame
input/visual test on this variant; `make atomic-test` runs both. This proves
no visible changes *between complete page swaps* under the tested emulator;
it does not certify physical hardware. Default raycaster tests still use
128x128, not the lower-resolution mode.

**Do not compare the number of 128x64 atomic swaps directly with the number
of 128x128 full-resolution redraws as if equal quality/pixel work**: the
atomic mode processes half as many logical pixels. The original articles
also discuss VRAM-to-VRAM DMA and optional multi-palette dithering, but those
are architectural observations, not implemented atomic 128x128 buffering
or native 256-colour graphics here.

See `../../workflows/paired_bat_plan.py`, which mechanically proves both
BAT mappings and emits TIA transfer dimensions:

```sh
python3 ../../workflows/paired_bat_plan.py --mode full
python3 ../../workflows/paired_bat_plan.py --mode atomic
PCE_HEADLESS=/path/to/rpc-capable/pce-headless make atomic-test
```

Historic technical references:
- https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/
- https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/
