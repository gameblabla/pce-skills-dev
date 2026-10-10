# 16-bit platformer physics and P4TR v4 (new default)

The HuC6280 is an 8-bit CPU. Avoid wide Q8 arithmetic for small worlds; for a
512×224 world use `int16_t` **Q4** in the authored game loop:

- World X: `0..7936` for a 16-pixel-wide player in a 512-pixel map.
- World Y: `0..3584`, within signed 16 bits.
- Walk: ±16 Q4 = 1 pixel/frame; gravity: +4 Q4; jump: −80 Q4; fall cap: +96 Q4.
- Camera: `(player_x - 104*16)` clamped to `0..4096`, using only 16-bit comparisons/additions.
- Platform collisions use the **same pixel coordinates** as the generated
  map. Feet cross a platform top only while falling and while overlapping X.

The Q4 algorithm and rules live in `examples/26-platformer-starter/src/platformer_q4.h`,
with the same file in example 27. The `test_p4_physics.py` host test runs 2,331
control ticks through real C and checks each tick against an independent Python
oracle. Avoid floating point and `int32_t` in runtime logic.

## P4TR v4 on target

Use `tools/p4tr.h`: two volatile, packed 32-byte slots. The writer first sets
an odd sequence value, then fills the record and publishes an even sequence.
Readers choose the newest complete record with `run + memread`; they never use
`trace_frames`. Fields are frame (16-bit), scene, flags, events, buttons,
world X/Y Q4, velocities Q4, camera Q4, drawn X/Y (pixels), racing lane and
progress (pixels), surface count and sprite count. Surface coordinates are NOT
in the trace: `p4_trace.py` reads `assets/platform_layout.h` independently,
which avoids accepting a fake collidable map supplied only by the game.

For a game with multiple genres, use explicit scene ownership. A new scene may
change the art and controls; do not carry platformer gravity into racing.

## Runtime acceptance

```
make platformer-check
PCE_HEADLESS=/path/to/pce-headless make platformer-test
make platformer-replay
make arith-games
```

Hybrid acceptance verifies: platformer movement crosses the stage boundary;
racing progress reaches its 480-pixel finish; the platformer returns with
reset camera; a subsequent 20-frame LEFT input advances game ticks and moves
the player again. This last check uncovered and fixed a real bug in the old
starter where VBlank continued but the per-frame SAT transfer hung. Example 27
now uses four direct `pce_vdc_poke` data words for each SAT entry and restores
only the background during handoff.

Only ROM + screenshot + input-script evidence together prove gameplay. Source
checks alone do not prove frame pacing; instrumentation alone does not prove
visible sprites. See `make genre-test` for unrelated game genres.

## Reproducible comparison

`workflows/perf_pair.py` builds both checkouts and takes Mednafen instruction
coverage for identical 240-frame idle input. The report includes BSS sizes,
linked arithmetic helpers and executed-PC counts. Emulator total instruction
counts include VBlank busy waiting; do not use them to claim FPS speedups.
This audit does not replace cycle-level profiling or a human visual review.
