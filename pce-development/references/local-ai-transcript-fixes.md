# Local coding-model failure fixes (four additional sessions, 2026-10-10)

This document describes **patterns**, not the private transcript text. Original conversations are neither committed nor required by these tools. The four sessions attempted the same ambitious one-minute Super CD-ROM² platformer; most stops occurred *before* runtime verification. They are not evidence of a functioning Super CD game.

## Run these commands, in this order

From the repository root:

```sh
python3 pce-development/workflows/offline.py route 'A one-minute Super CD platformer with title, enemies, stomp, flag, death and fade'
python3 pce-development/workflows/offline.py brief 'A one-minute Super CD platformer with title, enemies, stomp, flag, death and fade' --out game-brief.md
python3 pce-development/workflows/model_guard.py symbol VDC_SPRITE_HFLIP
python3 pce-development/workflows/assetpack.py pce-development/workflows/specs/pce-level.json --check
make agent-check agent-assets test
# Scaffold HuCard gameplay mechanics first; do not call it a CD build.
python3 pce-development/workflows/offline.py new --recipe platformer --out ./sandbox-platformer
cd sandbox-platformer && make model-check && make
# Use make run / make trace only if a suitable headless build is available.
```

To build a map from data without a player, scaffold recipe `level` instead. `examples/28-generated-level` is the reference with self-contained Makefile/asset generator. The data includes *metadata* for enemies and a flag; the tilemap example only **renders** the background. To make a full game, connect these entities to a real gameplay state machine and add scenario tests.

## Failure → check → safe action

| Observed failure class | Automated handling | Non-automated requirement |
| --- | --- | --- |
| Invented `KEY_A`, `KEY_START`, `VDC_SPRITE_HFLIP`; redefined joypad constants | `model_guard.py scan` (Makefile `model-check`); `symbol NAME` | Use the actual LLVM-MOS SDK headers (`KEY_1`, `KEY_RUN`, `VDC_SPRITE_FLIP_X`) |
| Oversized/mismatched hand-written C tile/map initializers | `assetpack.py --check` rejects invalid 8x8 patterns, variable BAT strides, bad glyphs and oversized maps; emits correct C `.c/.h` | Split large maps into verified streamed banks rather than deleting the level |
| Linker bank overflow, overlapping reset vectors | `model_guard.py diagnose LOG` classifies it | Inspect map, ROM windows and actual ownership; do not reassign sections or shorten levels without consent |
| `-Werror` unused variables left by unfinished title/fade/timer features | `diagnose LOG` | Finish feature or remove dead state; keep warnings enabled |
| Wrong normal Mednafen screenshot flags / GUI timeout / lockfile | `diagnose LOG`; project `make run`, `make debug` | Use configured headless frontend; a GUI that ran until timeout is **not** gameplay validation |
| Headless RPC missing `input`/`trace_frames` | `diagnose LOG`; `make trace`/`make hybrid-test` fail visibly | Rebuild/use RPC-compatible frontend; do not claim a trace on incompatible binary |
| HuCard works, requested *Super CD-ROM²* game | `offline.py route/brief` names target mismatch; `model_guard.py evidence` rejects `.pce`/`.bin` claims | Pack IPL+disc and cold-boot with user BIOS; packaging and CD audio must be tested separately |
| Claimed complete because binary exists | `model_guard.py evidence tools/evidence.json` requires distinct build, neutral, input and visual evidence | Add a reproducible scenario proving enemy side-hit, stomp, death/retry, flag, title, fade, and enough world length for ~60 s |

A model should not respond to a linker overflow by making a 60-second level only 128 pixels wide. Nor should it conclude a stuck GUI emulator proves the game is alive. These failure modes are caught or documented before further code generation.

## Explicit game-acceptance stages

1. **HuCard mechanics:** title-to-play button edge, grounded jump, wall/one-way platform collision, facing direction and camera clamp; P2TR walk/jump/land trace.
2. **Enemies:** one enemy is demonstrated as harmful on side contact and defeated by downward stomp; lives/death/retry reset camera, collision state and sprite SAT slots.
3. **Goal and timing:** flag exists in collidable world, reachable after a measured play duration (~3600 NTSC frames), goal animation plays fully, and win state prevents further movement.
4. **Presentation:** palettes fade with explicit frame steps; title, play, death and ending screenshots reviewed, along with no stale graphics after scene changes.
5. **Super CD packaging:** genuine IPL + CD image + user BIOS, **cold-boot** trace, boot/logo/sector tests and disc-specific audio checks. Merely compiling with a CD-ish executable name is not a disc build.

These are separate acceptance gates. `examples/26-platformer-starter` implements only the physics baseline; `examples/27-platformer-racer` implements two scene ownership/control domains; `examples/28-generated-level` implements an asset pipeline. **None is an entire one-minute Super CD game**. Report which gates are implemented, built, input-tested and visibly reviewed.

## Evidence manifest

Copy `workflows/specs/evidence-template.json` into your new project's `tools/evidence.json`, and mark stages **true only after recording reproducible evidence**. Then run:

```sh
python3 pce-development/workflows/model_guard.py evidence tools/evidence.json
```

The gate fails closed when an item is missing. Manifest booleans are **self-reported**, not cryptographically verified. A hardware check must only be claimed after console testing.
