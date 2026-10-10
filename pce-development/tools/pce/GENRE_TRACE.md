# From P2TR to G2TR: trace any PC Engine game genre

**Preserve P2TR v1.** `platformer_trace.{h,py}` (two consecutive 216-byte records, detailed collision surfaces, landing/camera diagnostics) stays byte-for-byte compatible with examples 26 and 27. Don't reinterpret its fields or silently rewrite its memory layout. It is still the best tool for platform collision correctness.

**G2TR v2** is a _companion_ used for shooter, racing, raycaster, visual novel, and optional coarse platformer traces. `genre_trace.h` defines two packed 64-byte records in main RAM under the symbol `pce_genre_trace`, and `genre_trace.py` reads them using existing generic `run`, `input`, and `memread` headless RPC operations. The previously bundled emulator's `trace_frames` is fixed to the 432-byte P2TR v1 format; do not use that command for G2TR. The game publishes only complete even-sequence records; the runner selects the latest valid slot, times out if game frames stop, and rejects out-of-main-RAM reads.

## Field contract

| Field | Meaning |
| --- | --- |
| `magic`, `version`, `genre` | ASCII `G2TR`, version 2, genre 1..5 |
| `scene`, `flags`, `frame`, `buttons`, `sequence` | Game scene, actor visibility, frame counter, active-high pad bits, odd=in-progress sequence |
| `x,y,vx,vy,camera_x,camera_y,screen_x,screen_y` | Signed Q8 coordinates and velocities; don't mix world pixels with screen pixels |
| `state[4]` | Genre-specific counters and state identifiers below |

`G2TR_VISUAL_NOVEL`: background ID, portrait ID, mouth open (0/1), dialogue ID. Detect mouth without portrait, invalid state, dialogue regressions. Independent screenshot test must show a mouth change confined to the portrait without changing the background.

`G2TR_SHMUP`: live bullets, live enemies, shots fired, damage taken. Check nonnegative counts, total bullet budget versus 64 SAT sprites, and no unexpected shot counter reset. **Do not use total bullets=64 as a gameplay guarantee:** reserve SAT entries for player, enemies and UI in your own engine.

`G2TR_RAYCASTER`: rays cast, rays hitting walls, nearest and farthest wall distance in Q8. Verify hits<=cast, positive ray budget and sane distance ordering. For correctness of clipping, fish-eye compensation or wall-column rendering, add screenshot and depth-buffer probes; telemetry alone does not prove texture projection.

`G2TR_RACING`: lateral lane (Q8), forward distance (Q8), forward speed (Q8), visible traffic count. Verify forward progress, nonnegative speed and sprite budgets. Example 86 still implements the separate 512×224 paired-BAT pseudo-bitmap Mode 7 road; the G2TR probe intentionally draws nothing.

`G2TR_PLATFORMER`: grounded, animation ID, collision count, camera lock. Generic coarse metrics only—prefer detailed P2TR v1 for actual jump/landing/feet-versus-platform checks.

## Run it

```
make genre-check                         # no emulator/compiler/network
make genre-build                         # compiled PCE HuCard probes + visual novel
PCE_HEADLESS=/path/to/pce-headless make genre-test
```

The individual probe projects (examples 30-32) intentionally publish trace records but **no pixels**, so the screenshot should be blank. They are NOT gameplay examples. The actual visual novel (example 29) emits its own G2TR records and displays a unique background with a hardware sprite. Use `make trace`, `make visual-test` and inspect the raw PNGs before making any visual-completion claim. Each example owns its tools so `offline.py new` creates a standalone project.

An offline scenario is a JSON object with `steps` (1..32 held-input segments of 1..3600 frames), optional `require_genres`, and optional `require_state_variation` mapping genre names to `state[0..3]` indices. Example: `{"steps":[{"frames":80,"buttons":[]}],"require_genres":["visual_novel"],"require_state_variation":{"visual_novel":[2]}}`. The runner captures exactly one completed record per step frame. Failed or absent publications are errors, **not a successful 80-frame run**.

## Evidence contract for agents

- Host-only trace fixture: verifies encoding and validator logic, NOT the game.
- Compiled ROM: verifies linking, NOT graphical or input behavior.
- Scripted emulator trace: verifies game-authored RAM values changed, NOT whether those pixels were actually drawn.
- Two emulator screenshots + localized difference: verifies closed/open frames visibly differ in the intended area; it still does NOT prove lipsync, audio, or hardware.
- Claim a complete visual novel, shooter, racer, or raycaster **only after genre-specific gameplay acceptance tests** (collision/weapon hits, projection, scene transitions, full dialogue scripting, etc.) exist and pass.

## Rendered examples and independent acceptance checks

Examples 33–35 add working rendered companions to the intentionally invisible
probes 30–32. `make visual-games-build` builds them; `make visual-games-test`
runs their G2TR scenarios and **independent emulator screenshot differences**.
The scripts use common `run`, `input`, `memread` and `screenshot` headless RPC,
not the platformer-only `trace_frames` API.

A given G2TR tick may take more than a single emulator frame (particularly
when redrawing the raycaster BAT). The reader polls for a *fresh committed*
record for up to sixteen frames and fails on stalling; it does not assume
one emulator VBlank equals one gameplay update. The independent visual test
checks that pixels changed in an expected scene region, that the reported
controller mask matches what was applied, and that screen-X movement has the
required sign. A rendered demo still doesn't verify collision completeness,
physical console timings, or 60 FPS.
