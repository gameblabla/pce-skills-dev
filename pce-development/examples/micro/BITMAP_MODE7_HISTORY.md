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

**86-mode7-bitmap-floor** starts with the *same* 128x128 bitmap texture, then
creates a separate 128x128 screen bitmap by sampling each perspective scanline
with starting U/V and DU/DV in fixed-point Q7. The source is a circle and the
output is the projected ground shape. LEFT/RIGHT changes between 16 headings
and triggers a new conversion/upload. The source and output use 4096 bytes of
RAM total (2x2048), which fits in an unexpanded PC Engine's 8 KiB work RAM.
The tiles are transferred with direct VDC word writes; disabling background
while updating prevents showing half-finished frames.

These are **educational simplifications**, not an Arcade Card port, a 60 Hz
bitmap framebuffer, or a claim that the PC Engine has a real Mode 7 or bitmap
mode. The second example uses one scanline per projected strip rather than
19 strips, and stores the source bitmap in normal work RAM instead of Arcade
Card RAM. It rebuilds a full image *only on a directional key edge*: uploading
8 KiB of VRAM every frame in plain C would be far too expensive for a real game.
For higher performance, the historical strip/2-pixel-pair and double-buffered
BAT approach, assembler sampling, and Arcade Card data streaming are the next
steps; they are deliberately kept out of these two single-purpose C lessons.

No Saber Rider graphics, sound, or game logic was copied. Both examples are
ordinary HuCard builds with no BIOS, CD-ROM, Arcade Card, or SuperGrafx needed.
