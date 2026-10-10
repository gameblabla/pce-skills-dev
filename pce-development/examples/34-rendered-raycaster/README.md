# 34 — fast 128×128 VRAM-resident raycaster (HuC6280)

This is a **real 32-ray textured raycaster** using the paired-BAT technique in
[PCEdev's Wolfenstein article](https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/)
and [bitmap-mode article](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/).
It sets physical **512×224** and keeps **128×128 logical 4-bit pixels** in the
VDC's 128×64 BAT, with two pixels per word and 256 fixed glyphs. It is **not**
128×64 atomic mode and does not create 8×8 planar tiles every frame.

## What changed: stop rendering the entire picture every update

The old default rendered **all 8,192 BAT words** through per-pixel C branches,
then staged 1 KiB in CPU RAM, waited for VBlank and uploaded complete rows.
That architecture, rather than the HuC6280's theoretical pixel fill, explains
why the example was much slower than the PCEdev estimated engine.

The fast **full-detail** default now:

1. Generates an exact **16 KiB screen-anchored sky/earth BAT backdrop offline**
   (`tools/gen_backdrop.py`) and installs it in VRAM once at startup.
2. Casts 32 actual map rays only when the camera position or angle changes.
3. Compares wall depth, texture phase, height and shading against the last
   drawn view. Unchanged columns incur **zero VRAM writes**.
4. Writes only the union of old/new wall spans, using the VDC's
   **+128-word vertical VRAM auto-increment** rather than rebuilding the sky,
   floor and every BAT row.
5. Sends at most **eight BAT words (16 bytes)** per HuC6280 `TIA` burst,
   enabling raster IRQs between bursts. Longer 16/24-word bursts caused real
   emulator screenshot failures and are rejected.
6. Uses a separately generated **127-event sparse raster IRQ**
   (`tools/gen_sparse_irq.py`), updating BYR at logical row transitions rather
   than running the interrupt for all 223 physical scanlines. This sparse
   version works because there are no long interrupt-masked VBlank transfers.

The 8×8 map, textured stone/brick/metal, collision, distance shading and
hardware bitmap mode remain. Rendering updates progressively on the visible
BAT, with tearing possible. The background is **screen-anchored** to avoid
expensive perspective-floor reconstruction on camera translation; wall
geometry is fully ray-cast from the current camera. A dynamically scrolling
floor remains a separate rendering-quality task. The ROM is 32 KiB, larger
than the old 8 KiB binary, but work-RAM BSS fell from 1,331 to 487 bytes.

## Generated HuC6280 vertical wall code (PCEdev-inspired, implemented)

The full-detail default now **executes generated wall microcode**, rather
than only linking a precomputed texture table. Run
`python3 tools/gen_wall_codegen.py` to regenerate `src/wall_codegen.S`;
`make tables-check` fails if the file is stale. The generator converts each
wall height (23 distinct values for 33 distances) into unrolled eight-row
instruction sequences. Each embeds scaled texture V addresses in `LDA
ray_codegen_pixels+constant,X`, then writes two duplicate-height pixels
using direct `STA $0002`/`ST2 #$f2`. `X` selects one of 40 shaded
material/horizontal texture phases. There is no pixel loop, C array
indexing, software multiplication, or division in the generated path.

The **eight-word / 16-byte interrupt limit still applies**. C positions the
VDC's +128-word vertical address pointer, disables IRQs for exactly one
specialized 8-pixel block, then restores IRQs. Any clipped span before/after
the unrolled section uses the original scalar/TIA path. The scalar prefix
*must stop at the next texture-aligned eight-row boundary*; otherwise the
C batches stay permanently misaligned and the generated writer rarely runs.

The generated source includes full ELF function size metadata for each
specialized code path; the emulator cycle profiler can attribute these
instructions rather than treating them as unmapped time. Duplicate wall
heights share the same ROM routines, so the complete 128×128 variant still
fits a **32 KiB HuCard**. This is one concrete implementation of the
[PCEdev code-generation concept](https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/),
not the blog's entire proposed engine or its anticipated FPS.

The same-source `-DRAY_WALL_CODEGEN=0` reference retains the previous
C/TIA wall writer, while `make atomic-rom` is still separately selectable
at 128×64, unaffected by this optimization. To reproduce the benchmark:

```sh
make codegen-reference tables-check
PCE_HEADLESS=/path/to/rpc-capable/pce-headless make codegen-benchmark
```

The 540-video-frame comparison observed **17 vs 19 changed-view commits
while turning** (5.667 vs 6.333 changed views per emulated second).
The generated routines uploaded **75,408 BAT words** out of **104,698**
across the measured segments (~72%). The independent stationary screenshot
matched **135,520 RGB pixels exactly**. Other segments may progress to
different map positions because faster builds advance more game ticks;
this is *not* an identical-work CPU cycle comparison, nor a measured
physical-console FPS. The original blog's 12–30 FPS projections have not
been reached; scene complexity and progressive presentation still matter.

## Reproducible measurements (emulated hardware, not real-console timing)

The previous renderer completed 19 *full background-and-wall BAT passes* in
1,080 emulated video frames (and recalculated unchanged frames). The new
renderer records **only completed changed-column views** and actual
`ray_bat_words` written to VRAM. Those measurements are intentionally not
called equivalent full-frame work, nor is their ratio advertised as a generic
3D engine speedup.

Use an RPC-capable headless emulator:

```sh
make tables-check
make
PCE_HEADLESS=/path/to/pce-headless make column-regression
PCE_HEADLESS=/path/to/pce-headless make column-benchmark
PCE_HEADLESS=/path/to/pce-headless make bitmap-test visual-test interaction-test
```

`column-benchmark` includes warm-up, idle, rotation, movement, settling and
quiet periods, plus five/six independently captured screenshots. It rejects
fabricated dirty-view counts without actual BAT writes and idle-rendering
loops that would falsely inflate FPS. The final benchmark measured **23 changed-view commits in 540 video frames**,
including **17 in 180 turning frames**, or **5.667 changed-view commits per
emulated second while turning**. A separate 1,080-frame stress test recorded
64 dirty-view commits. These are not atomic images or guaranteed continuous
motion, and this turning rate remains below PCEdev's projected **12–15 FPS
for typical action / up to 30 FPS in open areas**; the original blog figure was an *estimate
for a more specialized precomputed vertical texture-code engine*, not a
benchmark of this ROM. The CPU cycle-profile and frame-upload tests remain necessary before
claiming any further performance result. Measured under 60-frame turning
input: ~148,843 master-clock ticks per emulated video frame in
`column_upload`, ~41,942 in `cast_scene`, and ~52,175 in `irq_vdc`.
The generated eight-word vertical instruction paths now exist and are
measurably useful, but the surrounding C clipping, dispatch and VRAM setup
still dominate. A more complete 15 FPS engine would require moving more of
those operations into generated native code; increasing interrupt-masked
transfer size risks raster starvation. Neither VRAM-VRAM DMA clearance timing nor physical console
frame rate has been measured.

A stationary picture rendered by this engine matches the original shader's
emulated screenshot **pixel-for-pixel**. The new code keeps real input-driven
wall blocking and G2TR evidence; neither the trace nor a screenshot alone is
proof of actual hardware timing.

The legacy row shader and old branch-per-texel shader are retained as
independently compilable reference variants. Their old full-redraw counters
are **not** compared with the new dirty-column counter as though equal work.

## Two distinct presentation modes

- **Default:** full 128×128 image, vertical dirty-column updates, with
  `src/bat_sparse_irq.S` and 32 KiB HuCard. Has full detail, but not atomic
  presentation.
- **`make atomic-rom`:** original independently compiled 128×64 VBlank-page
  swap using `src/bat_bitmap_irq.S`, 8 KiB HuCard, lower vertical detail.
  Mirrored/symmetric top/bottom scenes could suit it, but are not implemented
  or silently enabled here.

## Alternate atomic presentation: trade vertical detail for two VRAM BAT pages

**Default (`make`)** remains **128x128 logical pixels**, which
fills all 8,192 BAT words: no second full-resolution BAT page exists. This is why the default still publishes short vertical dirty-column bursts
progressively, even though it no longer uploads the whole background.

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

## Wolf texture sheets: real source art, packed at build time

Both user-provided source atlases are vendored as `assets/wolftextures16.png`
(7 textures of 32x32, with 15 actual RGB colours) and
`assets/wolftextures256.png` (7 textures of 32x32, 105 actual RGB colours).
No art generation or web access is required.

`python3 tools/gen_texture_sheet.py` reads the **16-colour** sheet and emits
`src/sheet_pairs.h` and `src/sheet_palette.h`. The 128x128 full-detail HuCard
uses all 15 source colours plus an independent VCE backdrop entry. Each tile
is sampled down to **16x16 logical texels** (not 32x32 on screen). Seven
materials and two distance/orientation shades become 14 material styles,
with 16 horizontal phases and 16 vertical phases. The 3,584 paired-BAT
values are precomputed; there is no per-pixel quantization or multiply in
runtime C. The generated assembly reads the same packed values.

`tools/gen_backdrop.py` losslessly reduces the 128x64 background's 8,192
BAT words to **14 unique 64-word rows plus 128 row indices**, keeping the
32 KiB HuCard layout possible. The ROM stores these row templates and
uploads the full image to VRAM only at boot. This saves ROM, not active
frame time. `src/wall_codegen.S` now embeds the 14 material/shade styles
and can select the VDC word address with native ST0/STA writes; the C/TIA
variant is kept for a fair same-art performance comparison.

To regenerate or verify every offline input:

```sh
make sheet-art-sgx       # verifies PCE and SGX asset converters, no compiler
make sheet-fps-check     # compares native VDC setup to legacy with same textures
make codegen-benchmark  # compares generated wall writing to C/TIA (same art)
make atomic-test        # separate 128x64 mode, not claimed same resolution
```

The benchmark that uses the user texture sheet and the same 540-video-frame
script records **6.0 changed views/s for generated assembly versus 5.0 for
C/TIA**, with 73.2% of uploaded BAT words passing through generated code.
This is a same-scene comparison of two rendering paths, **not proof of an
improvement over the previous synthetic-texture release or 60fps**. The
native VDC-setup change alone delivered no measurable changed-view gain in
its separate 960-video-frame benchmark (25 versus 25 turning views).
There is a single physical scanline difference at the 64-row BAT page latch
between the C/TIA and assembly ROM captures (492 of 135,520 RGB pixels),
which is reported instead of being hidden by an "exact screenshot" claim.

### SuperGrafx: honest two-VDC asset preparation, not yet a runtime engine

`python3 tools/sgx_texture_plan.py` produces `src/sgx_texture_planes.h`,
`assets/sgx_dual_plan.json` and `assets/sgx_dual_preview.png`. It quantizes
seven source textures into at most **15 opaque base colours plus 15 overlay
colours per texture**, allocating independent colour-0 transparent slots.
The 7,168 bytes of packed nibble planes cover 32x32 texels per texture and
would be mapped to the two independent VDCs. The preview is composited on
the host and has an average 3:3:3-quantized RGB-channel absolute error of
6.903 against the richer source artwork.

**No SuperGrafx ROM or VPC compositing has been implemented or tested in
this update.** The SGX paired-BAT trick is discussed as approximately
128x128x241, rather than arbitrary true 256-colour pixels. The real dual-VDC
engine still needs palette selection per BAT entry, VPC priority, independent
scroll interrupts, and an emulator/hardware capture proving the blend. The
256-colour source file itself has 105 distinct source colours.

## Native-port fallback for short wall spans (full-detail only)

The generated eight-word writer handles aligned spans. For irregular
1–8-word leading/trailing spans, using `pce_memop`/TIA has appreciable fixed
setup overhead. The full-resolution default now uses direct VDC stores for
those **at-most-16-byte** transfers (`RAY_COLUMN_TIA=0`), preserving the
raster-interrupt limit. The old TIA behavior remains independently buildable.

Also, when two ray depths project to the **same wall height**, the generated
texture-V lookup is identical. A depth change without a change in projected
height, wall-style/shading, or horizontal texture offset is not a new image.
`RAY_CANONICAL_WALL_KEY=1` avoids that redundant dirty-column upload, and an
offline test exhaustively verifies the height-to-V-table identity.

```sh
PCE_HEADLESS=/path/to/rpc-capable/pce-headless make scalar-fps
```

This compiles both full-detail ROMs from the *same source* and 16-colour atlas,
executes each through the emulator with the same controller schedule, samples
real changed-view and BAT-word counters, validates the captured pictures,
and compares stationary views independently. The atomic 128×64 build is
**separate**, not used as an apparent FPS gain. The test is not a fixed-work
cycle comparison because two ROMs can advance to different scene positions.

In the current 540-video-frame emulator scenario, the short-span TIA reference
completes **6.000** changed views/sec while the direct-write full-detail ROM
completes **6.333** (5.55% more). The independent stationary comparison has
**zero different pixels** across the 560×242 emulator capture. The linked ELF
`.bss` falls from **724 to 692 bytes**, and `.text` from **9,686 to 9,644**
bytes. These measurements are specific to this scenario and compiler, not a
prediction of actual console frame rate or a replacement for the much larger
pixel-fill optimizations described by PCEdev.
