# 26 — Runnable platformer starter (HuCard)

This is a complete **bootable movement/collision sandbox**, not a feature-complete one-minute game. The starting screenshot contains original indexed background artwork, layered platforms and a 16×16 hardware player sprite. LEFT/RIGHT moves the sprite in world X. A *new press* of I jumps; Q8 vertical velocity accumulates gravity and landing snaps feet to a crossing of a platform top. The camera follows the actor without modifying world physics.

```sh
make
make run            # neutral pad screenshot; requires PCE_HEADLESS
make trace          # deterministic held buttons; needs RPC trace_frames frontend
```

The `tools/platformer-scenario.example.json` drives `make trace`. The standalone **P4TR v4** tool reads two 32-byte records (64 bytes total), and validates positions/landings against the independent `assets/platform_layout.h` source, not self-reported geometry. The game uses **16-bit signed Q4** movement, camera and velocities; no 32-bit physics or linked arithmetic helpers.

`src/demo_video.c` and `assets/demo_assets.h` are simple original background/sprite fixtures. This project does not yet implement a title, enemy combat, lives, goal pole, fades or CD-ROM² IPL, and a screenshot does not prove gameplay. Build in those features one by one from other focused recipes with a new scenario for each.

### Compact 16-bit P4TR tracing

- `src/platformer_q4.h`: strictly 16-bit Q4 physics and camera in a 512×224 world. Signed velocities never require wide arithmetic.
- `tools/p4tr.h`: two 32-byte records published with an odd/even sequence guard.
- `tools/p4_trace.py`: generic RPC `run` + `memread`, with external platform geometry. The old P2TR 432-byte window and special `trace_frames` command are **not used**.
- `make trace-replay` rechecks saved captured samples offline, with no emulator.
- `make arith-games` at the repository root audits linked ROMs for multiplication/division helpers.

A successful state trace does not establish that graphics are correct; use `make run` and check emulator screenshots separately.
