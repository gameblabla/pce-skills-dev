# Offline development workflows for PC Engine local AI

These scripts **do not call an LLM, the internet, GitHub, or a package manager**. They do not need the transcripts at runtime. `route` provides a deterministic entry point for smaller text-only coding models that might otherwise invent game code, switch compilers or draw debugging graphics in audio examples.

Start at the repository root:

```sh
python3 pce-development/workflows/offline.py doctor
python3 pce-development/workflows/offline.py route "I want a Contra-style game with platformer and racing segments, X/Y rules"
python3 pce-development/workflows/offline.py new --recipe hybrid --out /tmp/my-hybrid
cd /tmp/my-hybrid && make && make run
```

For a pasteable local-model implementation contract, run `offline.py brief "platformer plus racing" --out my-ai-brief.md` and give that brief to Luna/Leading Edge AI. The output is a deterministic instruction document, not an API call. The `new` command does not overwrite anything. The hybrid project carries its own JSON spec and offline generator; `make rules-check` validates it, `make simulate` writes a host-only simulation result, `make` compiles the ROM, and `make run` captures neutral-input emulator output. The original project is always left untouched. The `audio` and other micro recipes scaffold an extra `micro/` and `starter/` directory so their shared helper paths keep working. CD projects copied this way are only **HuCard previews** until an actual IPL and disc packager are added.

From the repo root, `make help` enumerates supported orchestration targets. Run `make test` without the SDK to validate the rules, static separation, and pure Python tests. `make games-build`, `make micro-build` require `mos-pce-clang`. `make game-run` requires `PCE_HEADLESS`. `make hybrid-test` requires a headless build with `input`, `run`, `memread`, `screenshot` RPC commands. `make trace-test` requires the newer RPC `trace_frames` command and an LLVM-MOS symbol file. **The older prebuilt emulator may run screenshots but cannot drive button scenarios.** Use a headless build from the included updated source if that is needed; do not misrepresent a neutral screenshot as a playable game test.

## Independent commands

| Program | What it actually checks | What it does not prove |
| --- | --- | --- |
| `offline.py doctor` | Paths to installed compiler / `make`, presence of emulator/BIOS environment variables | Matching SDK revisions or a real CD boot |
| `offline.py route REQUEST` | Selects an existing recipe by transparent string patterns | Model understanding or generated game correctness |
| `offline.py new --recipe ... --out ...` | Copies source/assets/SDK Make rules without cached build files; refuses overwrite | That the project builds on the user's machine |
| `offline.py validate SPEC` | Bounded coordinates, platform rectangles, two-scene reachability, fixed-point ranges, lane bounds | Visual alignment or physical collision |
| `offline.py generate SPEC --out FILE` | Deterministic `hybrid_rules.h` constants from validated JSON | Support for arbitrary extra scenes; the demo supports exactly two |
| `offline.py simulate SPEC SCENARIO` | Offline integer Q8 physics, lane limits and scene transition oracle | The ROM implemented the oracle correctly |
| `offline.py romcheck ROM` | Presence and 8 KiB bank alignment | ROM header validity, boot, audio, or gameplay |
| `source_lint.py` | Source-code invariants for world/camera/racing variables | Runtime physics correctness |
| `screenshot_check.py IMAGE ...` | Image dimensions, distinct colours, foreground pixel count, image differences | Character controls, frame rate or scene interactions |
| `animation_audit.py MANIFEST` | Missing animation states (including standing shoot), unsafe/missing frame references, invalid frame timing | Actual sprite availability when not configured to check paths, or animation behavior |
| `map_audit.py MANIFEST` | Shared drawn/collidable bounds and pixel-to-tile spans | Actual collision engine or on-screen alignment |
| `hybrid_runtime.py --rom ... --elf ... --out ...` | Real ROM scene flag transitions after held controller input; screenshots | Complete P2TR physics analysis, 60 FPS, hardware |
| `transcript_lessons.py sessions.zip` | Aggregate category presence per exported text session (no raw excerpts) | Failure severity, human intent or the validity of solutions |
| `tests/test_offline.py` and `tests/test_model_guard.py` | Invalid game rules, wrong SDK symbols, array/VRAM bounds, missing evidence | Emulator or gameplay execution |

## Hybrid game contract

The executable `examples/27-platformer-racer` is a **HuCard teaching skeleton**. Its gameplay segment contract is:

- Platformer phase: signed Q8 player **world X/Y**. RIGHT/LEFT walk at `walk_speed_q8`; I pressed freshly jumps with negative Y velocity; positive gravity pulls down. Land only when feet cross a solid platform top from above. Camera X is derived from world X and never modifies physics X.
- Racing phase: signed Q8 **lane X** is clamped to `race_lane_left`/`race_lane_right`. Holding UP advances unsigned Q8 **forward Y**. Platformer gravity and jump are disabled. The road background is an independent static BAT (offline-generated art), not an inaccurate substitute for the 512×224 Mode 7 example.
- Crossing X=`first platform length` enters racing; crossing forward Y=`first race length` returns to the platformer at its start. Phase ownership and camera reset on handoff; PSG is deliberately not initialized.
- A debugger symbol `hybrid_scene` is 0 during platforming and 1 during racing. `hybrid_race_progress_q8` and `hybrid_race_lane_q8` are separate telemetry. P2TR scene value **4** marks this demo's racing phase and is intentionally excluded from platformer-only P2TR collision diagnostics.
- This prototype does **not** have enemies, shooting, life/health, a title-to-game transition, fade animations, an authentic SNES Mode 7 engine, or CD-ROM² packaging. Use the existing focused shooter, sprite, audio, CD and Mode 7 recipes for those independent features and integrate one at a time with new tests.

Change the spec at `examples/27-platformer-racer/tools/hybrid.json`. The generated `src/hybrid_rules.h` is compiled into the ROM. `make rules-check` rejects a third scene instead of silently claiming to support it. The `workflows/specs/hybrid.json` copy demonstrates the same schema for routing. The `tools/build_race_art.py` generator makes original palette-limited tiles and a preview. After editing artwork, `make assets` regenerates the VDC patterns and BAT.

## Recommended local AI tool-call policy

1. On a game request call `offline.py route` before emitting code. If it returns `hybrid`/`platformer`, scaffold that existing runnable project instead of synthesizing new physics and Makefiles.
2. Write user X/Y, jump, camera, collision, stage transition and hardware scope into versioned JSON and validate it **before** generating C. Reject unsupported combinations (three phases, arbitrary SGX colour depth, CD-only ROM expected from HuCard target).
3. Make one gameplay change. Run `make`, then `make simulate` for independent rules; if supported run `make hybrid-test`/`make trace`. Pair scene-correct screenshots with actual input applied. Never turn a compile, a screenshot or a host oracle into a claim about live gameplay.
4. When bank full, run `scripts/bank_space.py` then inspect runtime overlays, loader scratch windows, IRQ owners and call sites. A free-byte result is not permission to overwrite a bank. For audio, keep VDC/VCE completely out of sample recipes.
5. Report a completion matrix: **implemented**, **compiled**, **headless neutral-output**, **input-driven trace**, **visual review**, **hardware validation**. Use “not tested” rather than guessing.

## Transcript-derived incident checklist

Review of the supplied exported conversations informed these recurring checks, without embedding or republishing transcript text: direction of camera movement, preserving fractional gravity, collidable tile indices versus pixel coordinates, sprite disappearance during transitions, stale generated art, sprite budget/SAT presentation, bank/overlay lifetimes, framerate versus emulator frame count, and confusing a HuCard binary with a bootable Super CD-ROM² disc. Those symptoms become independent lint/physics/trace/evidence gates rather than generic advice to “test everything.”

## New local-AI transcript hardening (four further sessions)

Read `../references/local-ai-transcript-fixes.md` for the incident classes, API corrections, and explicit acceptance stages. These sessions are private and are not packaged. The new tools are pure Python with no LLM calls or online access:

```sh
python3 pce-development/workflows/model_guard.py scan pce-development/examples/26-platformer-starter
python3 pce-development/workflows/model_guard.py symbol VDC_SPRITE_HFLIP
python3 pce-development/workflows/model_guard.py diagnose compile.log
python3 pce-development/workflows/assetpack.py pce-development/workflows/specs/pce-level.json --check
python3 pce-development/workflows/offline.py new --recipe level --out ./standalone-map
cd standalone-map && make assets-check && make && make run
```

`model_guard.py evidence specs/evidence-template.json` is an intentionally failing starting gate: a compiled ROM must not count as tested input/gameplay. `make agent-check agent-assets agent-build` runs source checks, validates data, and builds the new JSON-generated tilemap example. Both game-starter Makefiles now have `model-check`, `diagnose LOG=...`, and `acceptance-check` targets (the last fails until evidence is entered).

`assetpack.py` uses **8x8 tile pixel** strings, a 32/64/128-tile physical BAT row stride, 0..15 pixel colour values, and one full 16-entry palette. It enforces word alignment and BAT-versus-pattern non-overlap, produces the correct PC Engine four-plane 32-byte pattern format, and checks solid map glyphs/entity positions. Generated `.h` declarations and `.c` definitions are kept separate and regenerated automatically by project Makefile prerequisites. It does not invent gameplay around entity metadata.

## G2TR v2 across five genres + visual-novel assets (new)

`../tools/pce/GENRE_TRACE.md` defines a **genre-neutral 64-byte G2TR v2 record**. The old platformer P2TR v1 record and detailed collision diagnostics remain unchanged. `make genre-check` runs offline G2TR and static-image tests. `make genre-build` compiles examples 29–32; `make genre-test` also runs four real headless RPC input/memory traces plus the closed/open-mouth visual-diff assertion. For standalone copies, use `offline.py new --recipe visual_novel|shmup_trace|raycaster|racing_trace --out DEST`.

Example 29 uses a static 256×224 background plus a separate 16×16 animated mouth sprite. `vn_pack.py` creates reproducible source PNGs, validates sizes and sprite palettes, deduplicates background tiles, generates 4bpp characters/BAT/SAT-ready sprite patterns, previews, and a SHA/VRAM allocation manifest. Use `make assets` for a compact single background palette, or `make assets-multi` for advanced 16-palette per-tile static pictures. `make visual-test` compares **actual emulator** captures, requiring changes only in the mouth. This independently catches an AI that changes its trace variables while never drawing the mouth.

Examples 30–32 are intentionally nonvisual telemetry probes, *not* finished shmup/raycaster/racing games. They show exactly how to publish the genre schema and detect counters, depths, camera, and forward-motion errors in the real emulator. Combine with examples 10, 86 and other gameplay recipes, then write genre-specific acceptance scenarios; never infer a rendered shooter or raycaster from a blank trace-probe ROM.

## Rendered G2TR acceptance pipeline — examples 33–35

A no-graphics G2TR probe deliberately cannot prove that any pixel was rendered.
To bridge that gap, route an ordinary shmup request to example 33, a raycaster
request to example 34 and a conventional racer request to example 35. Explicit
*trace/probe* requests still route to examples 30–32. PCE paired-BAT Mode 7
requests still route to micro example 86.

These three HuCard ROMs use actual input and visible changes:

- **33:** movable ship and on-button-edge bullets, three enemies; telemetry
  counts bullets actually present in the SAT upload
- **34:** 32 real quarter-cell stepped map rays, producing distance-shaded
  BAT wall-height columns (not pre-rendered views); arrow keys move/rotate
- **35:** lane-controlled vehicle and distance-dependent traffic sprites;
  this is a racing-controls lesson, not a software Mode 7 emulator

The offline image generator `tools/pce/scene_pack.py` accepts **only** a
256×224 RGB background and a 64×16 RGBA sprite strip with exact 16-colour
palette. It enforces the sprite's reserved transparent index, unique-tile
budget and pattern/BAT/SAT VRAM separation. Generated output is deterministic.
`make assets` regenerates each visual demo's graphics and its byte-allocation
manifest; `make assets-check` works without any SDK or network.

`tools/pce/visual_scenario.py` captures independent emulator PNGs after
scripted button holds, verifies trace input latching, checks minimum distinct
colours, checks a minimum number of changed pixels, optionally checks changes
inside a scene-local rectangle, and verifies screen-X motion sign. A trace
alone, or a screenshot that never changes, fails the acceptance test.

```sh
make visual-games-build
PCE_HEADLESS=/path/to/pce-headless make visual-games-test
python3 pce-development/workflows/offline.py route 'make a raycaster game'
python3 pce-development/workflows/offline.py new --recipe raycaster_visual --out /tmp/my-raycaster
```

The tool permits a bounded sixteen emulator frames to obtain the next G2TR
game tick, because complex software rendering may take longer than one VBlank.
This prevents false failures on slower scenes without accepting a permanently
stalled game. No SDK/BIOS/image downloads are made by these validators.

### Narrow arithmetic and compiled-helper audit

`python3 arith_guard.py source ../examples` checks for newly introduced
32/64-bit types, floating point, suffixed wide literals, and libm/libgcc
link flags, retaining exact-line legacy exceptions.

`python3 arith_guard.py elf path/to/game.pce.elf` checks the final linked
symbols for software multiply/divide/modulo and floating math. `make
arith-build` enforces this on Mode7, BAT circle, and four 8/16-bit lessons.
For hardware-safe code, see `../libcommon/README.md`. Generic 16/8 long
division is a portable fallback; use a precomputed reciprocal or perspective
lookup for frame-critical drawing.

`make arith-audit-all` builds and checks **every micro-example ELF** for
software multiply/divide/modulo and libm symbols (as opposed to only the six
frame-math lessons). It checks the exact ROM count so a missing binary cannot
be mistaken for a clean audit.
