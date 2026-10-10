# 85-bitmap-128-circle

**Category:** Graphics

The **basic 512×224 HuC6270 pseudo-bitmap**, as explained in PCEdev's
[Wolfenstein post](https://pcedev.wordpress.com/2015/11/25/wolfenstein-3d-on-the-pc-engine/)
and [bitmap-mode post](https://pcedev.wordpress.com/2015/12/10/pce-bitmap-mode/).
Unlike a regular tile framebuffer, **128×128×4-bit logical pixels live
entirely in BAT words in VDC VRAM**. This draws a filled red disk as the
simplest possible use of the scheme.

- Set the display to **512×224 at the 10.7 MHz pixel clock**.
- Preload **256 constant 8×8 tile patterns**. Tile `0xab` is four hi-res
  pixels of palette colour `a` followed by four of `b`, for all 0..15.
- Write a row of **64 BAT entries = 128 four-bit logical pixels**. The lower
  byte of each entry holds the two colour indices; upper byte `0xf2`
  selects tile index `0x200 + pair` and background palette 15.
- Use a 128×64 BAT as **two 64×64 halves**, selected by the raster IRQ via
  `BXR=0` or `BXR=512`; adjust `BYR` to address logical row 0..127.
- The 128 virtual rows are stretched over the 224 physical lines by
  the raster remapper. Pixels are rectangular in a regular PNG capture;
  this is normal at the 512-dot-clock resolution.

No framebuffer in CPU RAM, no unique planar tiles per image, no sound,
font, sprite or Arcade Card. The reusable hardware implementation is in
[`../bat_bitmap.h`](../bat_bitmap.h). Build with `make`; run with `make run`.

**Teaching limitation:** Drawing into BAT during active display can tear;
this static example draws before enabling the display. IRQ-driven row
selection is precise enough for the supplied emulator, but has not been
verified on original PCE hardware.
