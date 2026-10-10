# 512x224 BAT-backed pseudo-bitmap and the old Saber Rider floor

## Why this is NOT a normal tile renderer

PCEdev's [Wolfenstein 3D on PCE (2015)](https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/)
and [PCE bitmap mode (2015)](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/)
describe the 512x224 / high-resolution raster trick:

1. In **512px VCE mode** the visible background is **64 BAT entries** wide.
2. Preload a fixed atlas of **256 8x8 tiles**. The tile number's upper and
   lower nibbles select the two 4-bit colours in a pair; the glyph renders
   each colour as four *physical* pixels, left and right. The tiles are
   constant across every bitmap frame.
3. Thus **one BAT word is two independent 4-bit pixels**, not a reference
   to a unique 8x8 patch of picture. With 64 entries/scanline there are 128
   *logical* pixels across a 512-physical-pixel-wide image.
4. A **128x64 BAT** is used as a **64x128 array of entries**: the two BAT
   halves (columns 0-63 and 64-127) store logical scanlines 0-63 and 64-127.
   The raster interrupt sets `BXR` to 0 or 512 and `BYR` to the corresponding
   logical BAT row times 8 for each raster line. This maps a **128x128
   4bpp logical bitmap** into just the BAT portion of VDC VRAM.
5. The screen remains a **512x224 physical raster**. The small demos stretch
   the 128 virtual lines over the 224 output lines with a 4/7 row step.
   This stretching is an illustration choice, not native PCE bitmap hardware.

`bat_bitmap.h` implements that arrangement. It owns the single VDC IRQ
handler, precomputes the glyph atlas, initializes display timing, and exposes
`bat_bitmap_row(y)` and `bat_bitmap_pair(a,b)`, both *VRAM BAT writes*. Writing
64 pairs in sequence finishes one 128-colour-index row. There is no CPU-side
image buffer and **no per-frame BG-pattern upload**.

VRAM layout (addresses in 16-bit words):

| VRAM | Contents |
| --- | --- |
| `$0000..$1fff` | 8192 BAT entries: 64x128 logical row pairs, physically 128x64 |
| `$2000..$2fff` | 256 fixed 4-bit-plane pair patterns x 16 words |
| `BAT word = $f200 | (left<<4) | right` | palette 15, tile `$200 + (left<<4 | right)` |

## Link to the historical Saber Rider engine

The [replacement commit a7e6089b850f](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/commit/a7e6089b850f)
on **2026-10-05** removed the previous pair-character floor and replaced it
with a classical static-background, scanline-scrolling racer.
The immediately preceding [floor_pce.c](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/src/platform/pce/floor_pce.c)
and [floor_sample.S](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/src/platform/pce/floor_sample.S)
show **the same BAT byte encoding**: one colour sample in each nibble,
fixed 256-character lookup, `$f2` as the BAT entry's high byte. Its
[projection parameter generator](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/tools/pce/floor_tables.py)
used 128 headings; the 19 perspective strips had seven farther bands
updated per eight raster lines and twelve nearer bands every four raster
lines. The hand-tuned sampler accessed its road/ground texture in Arcade
Card RAM and worked on the offscreen BAT page before presenting at VBlank.

The **replacement** classic racer did NOT use bitmap texels; its road was
one static perspectively drawn background image repositioned by BXR/BYR
for road curvature and stripe selection.
[Engineering notes](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/saturn-m3-m4/docs/PCE_CLASSIC_ROAD_20261005.md).

## Two independent lessons

- `85-bitmap-128-circle` creates the hardware BAT pixel buffer and plots a
  red filled circle: a pure example of *writing paired bitmap pixels*.
- `86-mode7-bitmap-floor` uses the same VRAM layout for a 128x128 colour
  perspective floor with road, kerbs and terrain. It projects one output
  scanline at a time, calculates U/V and DU/DV, then writes 64 packed BAT
  words (128 pixels). LEFT/RIGHT rotate the view, UP/DOWN moves the camera.

Both run from a **normal base-PCE HuCard**, without CD BIOS, Arcade Card or
SuperGrafx. They favour readable C over Saber Rider's fast hand-coded sampler
and skip its double-buffering/19-strip speed optimizations. Redraws occur
with the display disabled to avoid tearing. The VDC raster handler controls
scroll registers every physical line; original hardware timing still needs
verification. These are software projections, **not native SNES Mode 7**.

The SGX pseudo-bitmap approach discussed by PCEdev combines the **two VDCs**
for up to **241 effective colours**; it is *not* a native 256-colour 8bpp
framebuffer and is not implemented by these two base-PCE examples.

## Gradient/terrain correctness

The tiny Mode 7 demo now reserves palette indices 0–6 for seven ordered blue
sky shades (dark at the top, light at the horizon). Index zero is transparent
in PCE BG characters: for this renderer the VCE backdrop register is set to
the supplied palette zero so it cannot become an unexpected black stripe.
The ground uses the remaining nine colour indices. No cyan sample markers are
drawn in the grass. `check.py --smoke` checks the gradient ordering and the
absence of cyan ground pixels in an actual emulator frame.
