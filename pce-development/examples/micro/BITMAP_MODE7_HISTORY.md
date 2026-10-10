# Tiny bitmap and perspective floor: origin and limitations

## The historical implementation

The **Saber Rider Star Sheriff UnOfficial** PC Engine road, before the switch to a
conventional raster-scrolled racer, is available in the `saturn-m3-m4` branch's
history. The replacement commit was **a7e6089b850f (2026-10-05)**:

- [Replacement commit: conventional road instead of Wolf3D pair-character floor](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/commit/a7e6089b850f)
- [Old `floor_pce.c` at 174e90dc9262](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/src/platform/pce/floor_pce.c)
- [Old `floor_sample.S` at 174e90dc9262](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/src/platform/pce/floor_sample.S)
- [Old projection table builder, `floor_tables.py`](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/tools/pce/floor_tables.py)
- [Replacement's technical notes, `PCE_CLASSIC_ROAD_20261005.md`](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/saturn-m3-m4/docs/PCE_CLASSIC_ROAD_20261005.md)

The **old** textured ground used 19 BAT strips: seven far strips sampled every
8 lines (64 samples repeated in pairs) and twelve near strips every 4 lines
(128 samples, two adjacent pixels encoded as one pair character). For each
heading, a projection table supplied starting texture U/V and increments
DU/DV for each strip. The hand-tuned assembler sampled the road/ground texture
from Arcade Card RAM, packed two colour samples into a character identifier,
and the game updated one back BAT page over multiple passes before presenting
it during VBlank. There were 128 precomputed headings; the road wasn't drawn
pixel-by-pixel into a conventional framebuffer.

The **new** road introduced in the replacement commit instead stores a static
perspective road picture and changes BXR/BYR with scanline interrupts, much
like traditional 2D racing games. That is a different renderer.

## What these teaching examples implement

**85-bitmap-128-circle** shows a *logical* 128x128 monochrome bitmap, 2048 bytes
in CPU RAM, in a centered area of a standard 256x224 PC Engine screen. It
renders a red filled circle: set one bit per pixel; VCE colour 1 supplies red.
Conversion streams every 8x8 group as a unique 4-bitplane VDC tile. 256 tiles
consume 8192 bytes of **VRAM**, not CPU RAM. The 32x32 BAT references the tiles
for the center 16x16 area and a blank tile elsewhere.

**86-mode7-bitmap-floor** now demonstrates an actual 16-colour **textured racing
floor**, not the original red circle. It projects a virtual repeating 128x128
4-bit-per-pixel road/grass map in 128 projected scanlines. For each 8-pixel section of a scanline,
starting U/V and horizontal DU/DV are calculated once, then incremented across
its eight pixels (affine horizontal sampling). The map has curves, kerbs, dashes,
grass and sky. The generated screen is packed into standard PCE planar 4bpp
8x8 BG tiles, 256 tiles/8192 bytes of VRAM, using a tiny tile-sized scratch
buffer rather than allocating a full 8 KiB frame in CPU RAM. Update is
button-triggered (LEFT/RIGHT rotate, UP/DOWN move) and temporarily hides BG
while uploading; it is intentionally **not** a 60fps floor engine.

The older Saber Rider renderer used **a more efficient 16-colour pseudo-bitmap**:
128 samples across 19 scanline strips, two adjacent 4-bit ground samples
forming one of 256 pre-generated BAT pair characters, texture in Arcade Card
RAM, and VBlank-swapped completed BAT pages. This teaching version instead
uses the simplest reliable 4bpp planar tile upload and makes **no claim** to
implement the paired-BAT/scanline-remapping trick or the original frame rate.

Further hardware references, explaining why the BAT can be used as a compact
pixel buffer and why a 128x128 logical bitmap differs from the normal tile
format:

- [PCEdev: Wolfenstein 3D on the PC Engine](https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/)
- [PCEdev: PCE bitmap mode](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/)

The PC Engine has a 16-colour *per palette* tile pixel. The SuperGrafx has
**two 4bpp VDCs** and a priority combiner; PCEdev describes **241 effective
colours** for the special pseudo-bitmap configuration. This is often described
loosely as "256 colours" but is NOT a native 8bpp bitmap pixel format. This
example targets the base PCE's 16-colour case only, not SGX compositing.

No Saber Rider graphics, sound, or game logic was copied. Both examples are
ordinary HuCard builds with no BIOS, CD-ROM, Arcade Card, or SuperGrafx needed.
