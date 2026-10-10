# 34 — textured bitmap raycaster (512x224 PCE mode)

Real Wolf3D-style raycasting, drawn through the **same paired-BAT bitmap
backend as the Mode 7 example** (`src/bat_bitmap.h`, kept in this exported
project). It sets 512x224 video and exposes a 128x128 logical 16-colour
framebuffer made out of BAT words, not per-frame planar graphics uploads.
Each BAT word stores two four-bit pixel indices in a fixed 256-pattern set.

32 signed fixed-step rays hit an 8x8 wall map. Rendering writes textured
stone/brick/metal walls, distance-varying wall heights, a ceiling gradient,
and a perspective checker floor **pixel by pixel into the BAT**. LEFT/RIGHT
turn and UP/DOWN move, sliding against solid walls. No sound or fonts.

`tools/gen_ray_tables.py` generates Q8 ray steps, wall heights and vertical
texture coordinates offline, avoiding runtime division/multiplication.
Regenerate with `python3 tools/gen_ray_tables.py`; `make tables-check` rejects
stale tables. `make`, `make trace`, `make visual-test`, and
`make interaction-test` exercise compilation, state and collision, and
independent rendered-pixel changes.

A *readable starter*, not a high-frame-rate Wolf3D engine: The renderer stages four logical rows per update in a 512-byte RAM buffer,
then uploads them ONLY during the next VBlank. This avoids starvation of
the scanline raster IRQ. The display stays enabled; a complete 128-row
redraw spans 32 game updates and appears progressively. Faster bitmap engines need dirty-strip tracking, tighter assembly samplers,
and HuC6280 cycle-level profiling.

## Independent visual check

`make bitmap-test` runs the actual ROM for 180 emulator frames and checks
for distinct ceiling, wall and floor colours, visibly textured wall regions,
and absence of the cyan palette holes seen in earlier Mode 7 prototypes.
The game emits G2TR telemetry separately: wall collision tests validate
actual map movement. The renderer's BAT writes are sliced across 16 game
updates, so a complete new viewpoint is progressive rather than instant.
