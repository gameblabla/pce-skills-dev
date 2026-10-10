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
