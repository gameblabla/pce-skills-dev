# 26 — Runnable platformer starter (HuCard)

This is a complete **bootable movement/collision sandbox**, not a feature-complete one-minute game. The starting screenshot contains original indexed background artwork, layered platforms and a 16×16 hardware player sprite. LEFT/RIGHT moves the sprite in world X. A *new press* of I jumps; Q8 vertical velocity accumulates gravity and landing snaps feet to a crossing of a platform top. The camera follows the actor without modifying world physics.

```sh
make
make run            # neutral pad screenshot; requires PCE_HEADLESS
make trace          # deterministic held buttons; needs RPC trace_frames frontend
```

The `tools/platformer-scenario.example.json` file supplies input for `make trace`. The trace symbol `pce_platformer_trace` publishes 2×216 bytes in main RAM. It includes source-of-truth collision surfaces plus drawn world/screen positions. Read [`../../references/platformer-rules.md`](../../references/platformer-rules.md) before changing collision, and audit the linker map for both trace slots before adding more RAM allocations.

`src/demo_video.c` and `assets/demo_assets.h` are simple original background/sprite fixtures. This project does not yet implement a title, enemy combat, lives, goal pole, fades or CD-ROM² IPL, and a screenshot does not prove gameplay. Build in those features one by one from other focused recipes with a new scenario for each.
