# G2TR game-rule acceptance and SAT admission (offline-first)

Use this after the first **rendered** genre example passes its basic `make trace`
plus `make visual-test`. It mitigates AI-generated "the object moved but the game
rules never executed" failures.

## How to reproduce

```sh
make test                  # offline; no SDK, firmware, network or emulator
make sat-check             # offline SAT admission example
make visual-games-build    # needs installed LLVM-MOS compiler
PCE_HEADLESS=/path/to/rpc-headless make interaction-test
make interaction-replay    # rerun all game-rule assertions on saved JSON frames, OFFLINE
```

Example 33 additionally runs `make combat-visual-test`. Its scenario presses Fire,
then checks that the center-screen enemy disappears **in a captured screenshot**
while G2TR enemy count decreases, shot count increases and player damage rises.
Its screenshot checks are not satisfied by changing RAM counters alone.

The last command uses the previous `interaction-test` run's per-game
`build/interaction-frames.json`. This is intentionally a separate artifact
from `interaction-report.json`: a skeptical reviewer can replay the exact
frame-by-frame evidence without running the emulator or trusting a log summary.
Replays are deterministic. To exercise a new game, copy one of the
`tools/interaction-scenario.json` files and change the steps and assertions.

## Events implemented by examples 33–35

- **Shmup**: fire a shot, let it overlap a live enemy, remove that enemy and
  projectile from the SAT, count the kill, and accept a separate incoming
  projectile hit on the player. `state` remains `[player_bullets,
  live_enemies, shots_fired, player_damage]`; bit 2 (`COLLIDING`) is latched
  briefly when either collision happens.
- **Raycaster**: walk forward into a solid map cell and stop/slide, never
  entering it. The audit checks the recorded camera position against an
  **independent** ASCII wall map supplied by the test, in addition to the
  collision flag and depth/column invariants.
- **Racer**: cross a checkpoint each 64 units of forward distance and
  complete a lap every 256 units; collide with visible traffic, apply a
  temporary speed penalty. `state` remains `[lane_q8, distance_q8,
  forward_speed_q8, visible_objects]`. Flag bit 3 (`TRANSITION`) marks
  checkpoints; bit 2 marks traffic contact.

Required event names: `shmup_enemy_hit`, `shmup_player_damage`,
`ray_wall_blocked`, `racing_checkpoint`, `racing_lap`, and
`racing_traffic_hit`. The offline G2TR runner **rejects** impossible
checkpoints, missing collision markers on enemy disappearance/damage, missing
required interactions, and raycaster positions in blocked tiles. It also
continues the old P2TR/G2TR validations.

An emulator may advance two game ticks between memory snapshots. G2TR accepts
adjacent captures at most three game ticks apart; collision/checkpoint flags
are latched for three ticks to make these edges observable. This is not a
license to advance more frames or to accept a result without evidence. A
missing event still fails the test, as do injected violations in the offline
unit suite.

## SAT admission before uploading sprites

```sh
python3 pce-development/workflows/sat_budget.py \
  pce-development/workflows/specs/sat-admission.json --strict
```

The offline planner checks legal sprite dimensions, visible bounds, 64 SAT
entries, 16 sprites/scanline, and 256 sprite pixels/scanline **per VDC**.
`vdcs=2` enables separate SuperGrafx VDC budgets. Priorities are applied to
prepare an ordered SAT list, so essential actors are admitted first and
optional actors can be refused before their patterns are touched. The
hardware does not magically perform this prioritization: the game must submit
SAT entries in the chosen order. Check the output `accepted`, `rejected`, and
`per_vdc` fields; `--strict` fails on budget overflow (but not fully offscreen
sprites). The planner assumes rectangular opaque occupancy and ignores
collision priority and hardware timing: do not claim it verifies rendering
without a screenshot.

## Evidence ladder (do not skip levels)

1. `make test`: JSON/schema and negative-test contracts only.
2. `make`: compiler and linker are successful, not proof of execution.
3. `make interaction-test`: native input + per-tick game-authored G2TR with
   actual emulator run; inspect saved `interaction-frames.json`.
4. `make visual-test`: independently capture emulator framebuffer changes.
5. Hardware/video/audio verification if the user requires timing/quality on
   actual console or Super CD.

The teaching racer here deliberately uses a fixed background and sprites; the
512×224 paired-BAT Mode 7 texture renderer remains micro example 86.
