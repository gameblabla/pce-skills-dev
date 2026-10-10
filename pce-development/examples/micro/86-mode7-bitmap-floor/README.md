# 86-mode7-bitmap-floor

**Category:** Graphics

A textured **Mode 7-style perspective road written directly into the 512×224
HuC6270 BAT-backed pseudo-bitmap**, not a circle and not a framebuffer made
from 256 unique 8×8 characters. No native Mode 7 hardware is assumed.

The old Saber Rider renderer sampled its ground texture into *BAT pairs*,
then selected its 19 perspective strips at raster time. This small HuCard
version instead computes a 128×128 projected colour-indexed picture and
writes the colour **pairs** directly to VRAM:

1. `bat_bitmap_setup()` enables the 512-pixel, 10.7 MHz VCE/VDC display,
   128×64 BAT addressing, palette 15, and **just 256 constant pair glyphs**.
2. `floor_draw()` performs software perspective sampling of a repeating
   128×128 road/grass source texture, with curves, dashed centre line,
   red/white kerbs, and sky. Every two 4-bit texels become one BAT word.
3. `bat_bitmap_display()` uses scanline IRQs to remap the BAT's two 64×64
   halves as one **128×128 virtual image** spread across 512×224 output.

**Controls:** LEFT/RIGHT rotate (16 viewpoints); UP/DOWN advance/back up.
Updates are button-triggered and drawn with interrupts/display disabled;
this example prioritises clear code, not the original game's frame rate.
No CD-ROM, Arcade Card, PSG, sprite or font is needed.

Unlike Saber Rider's old floor, this demonstration does not use its
**19-strip half-resolution far/near optimization**, Arcade Card sampler,
or asynchronous double-buffering. Those are separate performance strategies,
not part of defining the paired-BAT bitmap trick. This example genuinely
implements the hardware layout and raster row remapping described by PCEdev.

Sources: [old Saber Rider floor](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/src/platform/pce/floor_pce.c), [sample-pair assembly](https://github.com/gameblabla/SaberRiderStarSheriffUnOfficial/blob/174e90dc9262/src/platform/pce/floor_sample.S), [PCEdev bitmap mode](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/), [PCEdev Wolfenstein notes](https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/).

**Hardware scope:** Base PCE 16 indexed colours. SuperGrafx's 241-colour
compositing extension is **not** implemented here. Requires dedicated VDC2
and colour-combiner code; it is not a native 8-bit bitmap framebuffer.
