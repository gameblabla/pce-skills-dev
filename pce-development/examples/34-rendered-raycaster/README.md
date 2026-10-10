# 34 — actual 32-column raycaster (rendered)

A small fixed-point raycaster that samples a solid 8x8 map and draws 32 real
wall-height columns into background tilemap entries; no fake static-picture
telemetry. LEFT/RIGHT rotate, UP/DOWN walk. Source of truth is the `ray_hit`
loop. Rays hit walls on a quarter-cell step. The demo intentionally uses coarse
8-pixel-wide stripes for clarity and speed, rather than Wolfenstein textures.

`make`, `make trace`, and `make visual-test` separately prove it builds,
reports plausible G2TR state under input, and changes visible pixels.
