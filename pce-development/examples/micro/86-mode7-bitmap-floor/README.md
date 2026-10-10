# 86-mode7-bitmap-floor

**Category:** Graphics

A minimal **software Mode 7-style perspective** demonstration: a 128x128 1-bit bitmap contains a filled red circle, and the renderer projects that source onto a ground plane. The 128x128 output is uploaded as 256 background tiles. Press **LEFT/RIGHT** to rotate the view by one of 16 headings; this example has no animation timer, audio, sprites, fonts, or game logic.

`floor128_project()` uses fixed-point Q7 texture coordinates. Every output scanline chooses a perspective distance, starting texture U/V, and horizontal U/V step. This is conceptually based on the old Saber Rider PCE floor's per-strip affine map sampler (not its full engine). The historical implementation sampled 128 texture positions across 19 BAT strips, used Arcade Card memory and swapped completed BAT pages at VBlank; here the texture lives in 2 KiB regular RAM, the output in another 2 KiB, and rows are sampled at pixel granularity. It only updates on a new directional key press; it blanks the BG during the blocking 8 KiB upload to avoid displaying partial tiles.

See `../BITMAP_MODE7_HISTORY.md` for source-history links, limitations and what was intentionally left out. Build with `make`, then `make run` or `make debug`. This works on a base PC Engine HuCard (no Arcade Card required).
