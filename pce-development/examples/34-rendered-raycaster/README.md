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
The priority for a genuine 15 FPS engine is generated bank-aligned vertical
wall-texture write code as described in PCEdev, not larger uninterruptible
TIA transfers. Neither VRAM-VRAM DMA clearance timing nor physical console
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
