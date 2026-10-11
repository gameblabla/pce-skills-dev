# Experimental VCS-inspired grid-boundary traversal (128×128 PCE)

This research follows the VCS wall-height converter port in `vcs-port.md`.
The original MIT-licensed Atari source remains under
`pce-development/third_party/vcs-raycaster-reference/`.

## What is implemented

The experimental `RAY_GRID_CROSSING=1` caster tracks the last crossed tile
X/Y coordinates and skips **two sampled Q8 positions** only when both endpoint
coordinates stay in that same tile. Because each signed ray component moves
monotonically over two steps, the intermediate sample cannot cross a gridline.
The subsequent wall hit still uses the original half-step midpoint refinement,
wall material, hit cell, wall face and exact texture phase. This is an
**exact bounded grid skip, not yet a fully analytical VCS tangent-intercept
DDA**. The production default remains `RAY_GRID_CROSSING=0`.

The offline test `test_ray_grid_crossing.py` compares the two algorithms over
more than 200,000 actual 128-ray direction/position combinations, including
one-Q8-unit wall-boundary cases. `make grid-crossing-check` also compiles both
HuCard ROMs and checks independent rendered emulator images, a 540-frame
turning raster sweep, 1,080-frame movement stress, and like-for-like
controller-window counters. The midpoint BAT seam and bounded 136-word raster-paced
upload path are unchanged.

## Measured PCE results

| Measurement | Established 128×128 | Experimental grid skip |
|---|---:|---:|
| 1,080-frame benchmark game-loop updates | 1,056 | 1,057 |
| Completed dirty-view passes | 14 | 14 |
| Turning dirty-view commits/sec | 1.50 | 1.50 |
| BAT words uploaded | 60,281 | 60,281 |
| Stationary RGB differences | — | 0 of 135,520 |
| `cast_ray` attributed ticks/video frame, turn | 19,761.65 | 16,350.50 |
| `cast_ray` attributed ticks/video frame, walk | 7,323.30 | 6,907.85 |

The profiler comparison uses the same 60-frame turn/walk windows, with 53
and 57 game updates respectively in both builds. The grid skip reduces
attributed `cast_ray` self time, but **does not measurably improve screen
throughput**. The render/VRAM raster path still determines the visible
update rate. Inlining and other symbol-attribution shifts mean these
per-function ticks are not whole-program speedups. The observed +1 game-loop
iteration out of 1,056 is not evidence of a substantive improvement.

Use the established ROM for gameplay. The experimental build exists for
further grid-intercept and assembly tuning, not as a claimed fast release.
See `docs/vcs-grid-crossing-evidence.json` in this repository, or the freshly
generated `build/grid-crossing-evidence.json` after running the check.
