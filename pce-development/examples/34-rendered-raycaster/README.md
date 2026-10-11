# 34 — 128×128 VRAM-resident raycaster (HuC6280)

This is a **128-sample textured raycaster** using the paired-BAT technique in
[PCEdev's Wolfenstein article](https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/)
and [bitmap-mode article](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/).
It sets physical **512×224** and keeps **128×128 logical 4-bit pixels** in the
VDC's 128×64 BAT, with two pixels per word and 256 fixed glyphs. It is **not**
128×64 atomic mode and does not create 8×8 planar tiles every frame.

## Speed revision: compact backdrop LUT and deferred clean pairs

The default 128×128 build now uses an **826-word periodic backdrop ROM
lookup** instead of recalculating the dithered sky/stone floor for every
staged wall pixel. The LUT preserves every one of the 8,192 possible BAT
backdrop entries exactly; the source generator and offline tests verify
this, including the second BAT page and all horizontal repeats. The wall
compositor packs its two 4-bit texels using 8-bit arithmetic and adds the
fixed BAT high byte only once per word.

The 96-word-per-VBlank staging limit and 8-word IRQ-masked transfer bursts
are **unchanged**. A stage can now represent several dirty wall segments
and intervening clean BAT pairs; clean metadata is committed only **after**
all preceding real VRAM transfers finish. No new view starts mid-batch.

In the same 1,080-video-frame emulator input benchmark, this revision
performed **790 game-loop updates vs 729** (+8.4%), both at **1.333 dirty-view
commits/second during turns** and **45,733 actual VRAM words**. Game updates
and dirty-view commits are not complete-frame FPS. The stationary emulator
image is **pixel-identical** (135,520 RGB pixels), the 540-frame raster sweep
and 1,080-frame movement stress pass, and the cycle budget passes. Physical
hardware performance has not been measured. The previous ROM/baseline
remains in Git history (`15a3652`).

## Midpoint scanline repair (128×128 only)

The 128×128 raster's BAT page split at logical row 64 previously exposed a
**one-scanline copy of the bottom floor in the middle of the wall** on some
video frames. The HuC6270 can apply the horizontal page switch (BXR) before
the new vertical scroll (BYR); the first line of the new page therefore used
its physical BAT row 63, which originally contained the floor.

The second BAT half is now **circularly rotated by one tilemap row**:
logical row 64 occupies physical row 63, rows 65..127 occupy rows 0..62.
The raster IRQ and the background/wall address table use the same mapping.
The vertical column uploader additionally splits bursts at the rotated row
wrap (between logical rows 64 and 65), preventing writes outside the BAT.
There is no new planar upload, CPU framebuffer or extra work per ray.

The emulator's exact screenshot of the old ROM has **100% floor-row match**
on the stray center scanline, with abrupt transitions above and below.
`make raster-sweep` now checks every frame for this defect as well as sky-only
frames. In the verified 540-frame turn sequence, the floor-row similarity at
the seam stayed below 10.2%; the 1,080-frame movement stress, 231 offline
checks and the native cycle budget also passed. Turning throughput remained
0.667 completed dirty-view passes/second, not complete FPS. This behavior
is verified in the supplied headless emulator, not on physical hardware.

## Current visual-quality revision: retain source pixels, blend BAT texels

The **default** 32 KiB ROM now improves what is actually rendered, not the
number of rays (still 128):

- **32×32 original texture data** on near walls (`depth <= 8`); the previous
  renderer threw away half of both texture axes by downsampling to 16×16.
  `src/hires_texels.h` packs all 7 materials into 3,584 ROM bytes, and
  `ray_hires_v` indexes all 32 vertical texels. Distant walls keep the
  precomputed 16×16 variants to avoid wasting time on subpixel details.
- **3+2+3 physical-pixel filtering:** each BAT word still specifies its two
  independent four-bit logical texels. A fixed set of 256 VDC character
  patterns now displays three physical pixels of the left color, two pixels
  of their nearest-palette midpoint, then three of the right color. The
  midpoint lookup is generated against the actual 3:3:3 VCE colors and
  occupies 128 ROM bytes. This does **not** add logical resolution, but it
  reduces the abrupt four-pixel color seam with no extra runtime BAT writes.
- A generated procedural **dithered sky and textured stone floor** replaces
  the 14 repeated coarse backdrop rows. The initial 8,192 BAT words are
  prepared once with BG off; changed columns restore the exact same formula.
- **Staged VRAM transfers** prepare at most 96 textured BAT words in RAM
  before VBlank, then upload them in IRQ-masked bursts of **at most eight
  words**. Old column keys are committed only after the full span is written.
  This is necessary because doing the more detailed wall shading in the
  raster-critical upload caused reproducible sky-only failures. Use
  `-DRAY_STAGE_UPLOAD=1 -DRAY_WALL_CODEGEN=0` for this verified build.

The **128×128 logical size is unchanged**. At physical 512×224 a paired-BAT
texel is nominally four physical pixels wide. Filtering those hard edges
improves gradients, but it **cannot** provide arbitrary 256-wide wall detail;
that would require a different graphics/palette/pattern strategy and a new
performance and IRQ stability evaluation. Hardware timing is unverified.

**Measured on the headless emulator:** the default build passes a 540-frame
continuous-turn screenshot sweep without a blank/sky-only frame; 1,080 frames
of controller movement; a 600-frame pixel-identical stationary comparison
against the independent C reference; the native cycle gate; and the 229
Python offline checks (including pixel-exact 32×32 texture unpacking and
all 256 paired-palette blends). The 96-word staged path completes **0.667
changed-view commits/second during turns** in the 1,080-frame benchmark,
versus 0.333 in the previous 24-word raster-safe release. These are dirty-view
passes, **not full-screen FPS**; the visible image is updated progressively.
The separate 128×64 atomic ROM remains a lower-resolution presentation option.
The interaction RPC scenario specifies an explicit 180-frame boot warmup for
one-time 8,192-word BAT and 256-tile initialization; the subsequent 305
gameplay samples pass wall-collision and motion audits.

Reproduce with `make tables-check bitmap-test column-regression wall-lookup-visual
atomic-test`, and from the repository root `make test cycles-ray`, with LLVM-MOS
and the RPC-capable emulator configured. Generated texture sources should be
regenerated via `python3 tools/gen_texture_sheet.py` after changing artwork.

---

## Previous 128-ray revision: NES-inspired sparse projection and two-lane BAT

The full-resolution default now projects **128 horizontal sample rays**, one
per logical screen pixel. Every **single BAT word** still stores two independent
4-bit texels in VRAM; the left and right rays have their *own* wall cell,
face, projected height, material/shade and texture coordinate. Older 64-ray
versions treated the two screen pixels as a single ray with adjacent texels.
This is still the exact PCEdev tile-map pseudo-bitmap technique; neither a
planar framebuffer nor a per-frame CHR pattern upload was added.

On the HuC6280, two unrelated wall texels cannot reuse the old one-ray
vertical writer. `tools/gen_wall_codegen.py` now emits **dual-index 8-word
native writers** (`X` for the left ray and `Y` for the right). It combines the
high and low colour nibbles from two different sheet coordinates while the
VDC increments its address by 128 words. This fast path is only used when
both rays have matching wall top and projected height; mixed depths, edges
and transitions use independently composited scalar BAT words. An old-wall
and new-wall span union restores both halves before marking a pair clean.

As in classic NES raycasters, the expensive math and distance projection are
precomputed. `RAY_ADAPTIVE_RAYS=2` casts **one ray every four screen pixels**
where possible, then refines the remaining screen directions, *forcing true
intersection casts* at wall-face/cell changes, depth discontinuities, material
boundaries and texture wraps. This prioritizes corner topology; projected
heights and sub-texel phases are still approximations, not mathematically
identical to 128 exact DDA intersections. To disable interpolation entirely,
compile with `-DRAY_ADAPTIVE_RAYS=0`. The host reference checker exercises
270,336 ray samples over 8x8-map camera positions and all 16 angles, and
requires **zero fabricated wall cells or faces**. It also measures, rather
than conceals, remaining height/texture differences.

The previous 64-ray build achieved **6.33 changed-view commits/second**
during turns in the older 540-video-frame test. The first 128-ray eight-pair
prototype reached **3.00**, but missed raster IRQs during prolonged movement
and occasionally displayed a sky-only frame. Increasing the number of rays
alone is **not an FPS improvement**.

The previous **128-ray raster-safe configuration** finished each partial BAT
column over multiple VBlank periods, with **at most 24 BAT words** scheduled
per period. Each pair's old dirty key is updated only when its final segment
has been uploaded. The camera view is recast only after all 64 pairs of the
previous view are complete; a guard prevents an accidental jump across the
pass boundary. Sparse native raster IRQs and the generated dual-lane wall
writer are retained. Both the **1,080-frame movement stress** (six completed
changed-view commits) and a **540-frame screenshot sweep during uninterrupted
turning** pass; the latter recorded *at least ten real emulator colours in
every frame*, with no sky-only image. These checks are now in
`make column-regression`.

For that earlier configuration, under an **extended 1,080-video-frame benchmark** (90 idle, 180 turn right,
180 walk, 180 turn left, 360 settle, 90 quiet), this build measures **0.333
changed-view commits/second during turning**. These are finished dirty-column
passes, **not full-screen atomic FPS**. The stable 128-ray version is therefore
substantially slower than both the original 64-ray version and the faster,
raster-unsafe 128-ray prototype. The progressive display can still show
partial view transitions, and physical hardware timing has not been tested.
The optional 128×64 atomic variant uses page swaps at half vertical
resolution; it does not use the progressive 128×128 presentation path.

The VBlank scheduler affects instruction attribution in native profiling:
the enforced `main + column_upload` gate is **300,000 ticks/frame**, up from
290,000 for the older eight-pair scheduling. It includes idle waiting, so
its attributed CPU time is not synonymous with the cost of drawing pixels.
The separate `irq_vdc`, `cast_ray` and `cast_scene` limits remain enforced.

The two direction tables use exact 180-degree rotational symmetry: eight
stored angles, with sign reversal at runtime, retain all 16 camera angles
and all 128 ray directions. This removes **2,048 bytes of ROM lookup data**,
verified against the original integer step calculations.

The native generator masks the left and right texel nibbles *separately*.
Without both masks, unrelated colour bits from the right texture corrupt
the left half of a BAT word. The current 600-frame C reference comparison matches **pixel-for-pixel**
on a stationary scene. Earlier revisions had a reproducible 504-pixel
page-latch scanline discrepancy; exactness is checked explicitly rather
than inferred from a textured-looking image.

This follows the NESdev discussion of avoiding large CHR pattern updates,
using precomputed ray/distance tables and reducing drawing work, while
retaining PCEdev's much more appropriate VRAM BAT layout:
[NES raycaster discussion](https://forums.nesdev.org/viewtopic.php?t=12180)
and [PCE bitmap mode](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/).

To verify: `make tables-check codegen-benchmark`, `make atomic-test`, and
`make -C ../../.. cycles-ray` (with a compatible native RPC emulator).
`make column-regression` performs the long raster stability check, the
input-driven column benchmark and the consecutive-frame raster sweep.
The raster-safe and faster historical code remain separately identifiable
in Git so quality/performance decisions can be reproduced.

## Historical 64-column wall quality pass (2026-10)


The original build used 32 rays: each cast result occupied **two** BAT words
(four logical pixels/16 physical horizontal pixels), producing pronounced
vertical wall steps and oversized texture strips. That historical revision rendered
**64 wall samples, one BAT word (two logical pixels) per sample**. It remains
PCEdev's VRAM-resident paired-BAT bitmap mode: 256 fixed glyphs; each BAT
entry encodes two 4-bit pixel colours. **No software framebuffer or per-frame
planar tile uploads were introduced.**

To avoid doubling all map traversal, odd columns are interpolated from their
adjacent exact casts only on a continuous face of the *same wall cell*.
Texture-wrap seams, material changes, face changes, and sharp depth changes
trigger a real cast. Empty-cell marching skips unnecessary map probes, and
one binary midpoint improves hit texture coordinates over sampling the
overshot endpoint. The renderer now streams 16 instead of eight BAT columns
per game-loop update; one full 64-column dirty pass takes four calls, as
before, and generated eight-word vertical wall writes remain intact.

The same 540-video-frame emulator input benchmark (90 idle, 90 turn right,
90 walk, 90 turn left, 90 settle, 90 quiet) measured **6.33 changed views/s
on turns in the previous 32-ray build** and **6.33 changed views/s in this
higher-detail 64-column build**. The latter is *not a wall-clock FPS or a
performance speedup claim*: it is a 2x horizontal sampling quality improvement
at roughly the same emulated progressive changed-view rate. Rendering is
still not atomic, the floor still uses a screen-anchored VRAM backdrop, and
physical-hardware timing is untested. To reproduce, run `make column-regression`
and `make bitmap-test` with a compatible `PCE_HEADLESS` binary.

## What changed: stop rendering the entire picture every update

The old default rendered **all 8,192 BAT words** through per-pixel C branches,
then staged 1 KiB in CPU RAM, waited for VBlank and uploaded complete rows.
That architecture, rather than the HuC6280's theoretical pixel fill, explains
why the example was much slower than the PCEdev estimated engine.

The fast **full-detail** default now:

1. Generates an exact **16 KiB screen-anchored sky/earth BAT backdrop offline**
   (`tools/gen_backdrop.py`) and installs it in VRAM once at startup.
2. Resolves 64 wall BAT words representing **128 separately shaded ray
   pixels** only when the camera moves or turns. Conservative interpolation
   checks require matching wall cells/faces and continuous texture spans.
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
than the old 8 KiB binary, and work-RAM requirements are significantly lower than the old full-frame staging renderer.

## Generated HuC6280 vertical wall code (PCEdev-inspired, implemented)

The full-detail default now **executes generated wall microcode**, rather
than only linking a precomputed texture table. Run
`python3 tools/gen_wall_codegen.py` to regenerate `src/wall_codegen.S`;
`make tables-check` fails if the file is stale. The generator converts each
wall height (23 distinct values for 33 distances) into unrolled eight-row
instruction sequences. Each embeds scaled texture V addresses in `LDA ray_codegen_pixels+constant,X` and `ORA
ray_codegen_pixels+constant,Y`, then writes two vertically duplicated pixel pairs
using direct `STA $0002`/`ST2 #$f2`. `X` and `Y` select independent entries among 224 shaded
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

`column-benchmark` includes warm-up, idle, rotation, movement, extended settling and
quiet periods, plus five/six independently captured screenshots. It rejects
fabricated dirty-view counts without actual BAT writes and idle-rendering
loops that would falsely inflate FPS. The earlier *32-ray* benchmark measured **23 changed-view commits in 540
video frames**, including **17 in 180 turning frames**, or **5.667 changed
views per emulated second while turning**. This is archival context rather
than a measurement for the historical 64-column build. The historical 64-ray emulator run
recorded **27 commits in 540 frames** (19 during 180 turning frames) and **65
commits in the 1,080-frame stress test**. These are not atomic images or guaranteed continuous
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
  swap using `src/bat_bitmap_irq.S`, 16 KiB HuCard, lower vertical detail.
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

## 128×128 staged wall-pair cache (October 2026)

The active 128×128 renderer resolves wall height, shade, V-phase and the
ROM texture-strip addresses **once per paired BAT column**. Its inner
`stage_pair_words()` loop then reads the cached pointers for each pixel,
instead of re-indexing 3-dimensional ROM tables on every row. Both lanes
retain independently sampled 128-ray texture coordinates; neither the
32×32 close-wall art nor the seam-corrected second BAT page is reduced.
The original short **8-word TIA bursts**, 96-word VBlank budget and
staged-then-presented IRQ schedule remain intact.

In the fixed 1,080-video-frame emulator benchmark (`make column-benchmark`),
the preceding `c212a3e` build reported **790 game-loop updates**, 11
dirty-view passes overall and **1.333 completed turning passes/s**. The
cached-strip build reported **1,056 updates**, 14 passes and **1.500
completed turning passes/s**. In the independent 1,080-frame movement
stress, changed-view passes increased from 14 to 19. An independently
captured stationary view matches the old ROM exactly (**0/135,520 RGB
pixels differ**); the 540-frame continuous-turn raster sweep also passed.
These are *progressive changed-view commits*, not atomic full-frame FPS.

Larger VBlank budgets were tested rather than assumed safe: **112 words
failed** the long movement stress and **144 words produced a sky-only
turning frame**. Keep 96 words unless those failures are solved and tested
on real hardware. The native cycle budget and 233 offline tests pass.

## Center-first progressive update (October 2026)

At 128×128 the PCE paired-BAT trick requires a substantial number of VRAM
words to replace a dirty wall view. Instead of making the player watch the
image redraw left-to-right, the default uses an alternating **center-out**
order: pairs 31, 32, 30, 33, ..., 0, 63. All 64 pairs, all 128 independent
rays, 32×32 close-wall textures, and the corrected row-64 page mapping are
preserved. The VBlank budget remains **96 words**, with no longer IRQ-masked
bursts. Build with `-DRAY_CENTER_FIRST=0` to restore the linear order.

`make center-latency` builds both render orders from the same source and
captures real emulator screenshots after a short camera turn. In the fixed
scenario the central 128-pixel-wide view matches its settled final rendering
by **40 video frames** with the center-first order; at the same point the
linear order still differs at **1,318 pixels**, converging by frame 80. The
final 560×242 RGB screenshots are identical. Over the standard 1,080-frame
benchmark, both versions complete **14 dirty-view passes** and **1.500
turning commits/s**. This is a **latency/responsiveness** improvement, not a
higher full-screen FPS claim. Retain the raster sweep and movement stress
regressions before changing the upload schedule again.
