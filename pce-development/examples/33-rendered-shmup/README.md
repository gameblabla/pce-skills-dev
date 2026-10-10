# 33-rendered-shmup — rendered shmup G2TR example

A small, **rendered** standalone HuCard using real controller input. Unlike
example 30, this project shows actual sprites
and game state. The background and four sprite patterns are compiled offline
from 256x224 and 64x16 PNG files (`make assets`).

- `make`: compile the ROM (SDK required)
- `make trace`: scripted controller input and G2TR v2 checks (RPC emulator required)
- `make visual-test`: independent captured-image comparison (RPC emulator required)
- `make assets-check`: validate PNGs, palette and VRAM without SDK

G2TR values are authored by the game and are **not** proof of pixels: use the
independent screenshot test too. This is a tiny demonstrator, not a full game.

## Game-rule acceptance

Shooting a live enemy destroys it and removes its SAT entry; one deterministic hostile bullet can damage the player. Trace counters and collision flags must prove both events.

Run `make interaction-test` for an input-driven native game scenario and
`make interaction-replay` to revalidate the saved G2TR frames offline.
Both targets are intentionally separate from the screenshot `make visual-test`.
The rules and expected events are in `tools/interaction-scenario.json`.

`make combat-visual-test` adds a two-capture test of enemy disappearance,
player damage and shot counts. A held Fire step deliberately does not capture
an intermediate image: the RPC emulator can process zero game ticks in a
single host frame, and gameplay input must be sampled by the ROM first.
