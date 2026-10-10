# 85-bitmap-128-circle

**Category:** Graphics

The PC Engine has a tile-based VDC, **not a true bitmap video mode**. This example uses a 2,048-byte RAM **128x128 1-bit pixel bitmap** and converts its 8x8 pixel regions to 4bpp VDC character patterns. One screen pixel is one bitmap pixel; the 128x128 square is centered on a 256x224 display. Palette 0 is black and palette 1 is red, showing a filled red circle. No image files, fonts, sprites, sound, or interrupts.

- `bitmap128_clear(pixels)` erases the RAM framebuffer.
- `bitmap128_circle(pixels, 64, 64, 40)` fills a red circle using integer midpoint rasterization.
- `bitmap128_present(pixels)` uploads 256 unique 8x8 BG tiles (8 KiB VRAM). The BAT holds their addresses.

Build with `make`, run with `make run` (headless emulator). The bitmap source is single-bit to fit easily inside the HuC6280's 8 KiB RAM. The reusable drawing/upload code is in `../bitmap128.h`.
