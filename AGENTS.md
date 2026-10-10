# PC Engine development skill bundle

Start with [`pce-development/SKILL.md`](pce-development/SKILL.md). The skill
and examples are self-contained: do not assume a sibling game repository,
private BIOS, compiled emulator binary, or conversation export is present. The
bundle includes licensed headless source under `pce-development/third_party/`;
preserve its upstream and component license notices.

Do not put an emulator executable's name into a local coding-agent prompt or
ask the agent to launch one directly. Project `make run`, `make debug`, and
`make trace` targets select the configured headless frontend and own its
arguments. `make bios-check` prints the user-local placement folder when CD
firmware is absent.

For platformer work, read
`pce-development/references/platformer-rules.md` and
`pce-development/examples/25-platformer-integration/README.md`. Keep physics in
world coordinates, trace real collision and render state with P2TR v1, and use
deterministic `make trace` scenarios to check walking, gravity, landing, and
camera behavior even when the local model cannot inspect images. A text report
does not establish pixel appearance or physical-console behavior.

The bundle has an arithmetic helper at
`pce-development/scripts/calc.py` and a linker-report capacity ranker at
`pce-development/scripts/bank_space.py`. The ranker does not prove that a bank
can be safely reused; follow
`pce-development/references/banks-and-overlays.md`.

Run the local model evaluation from this directory:

```sh
python3 pce-development/scripts/eval_local_ai.py
```

Read `pce-development/scripts/README.md` for evaluation options and limits.
Run `python3 pce-development/examples/micro/check.py --lint-only` to guard
sound-only versus graphics-only examples when changing them. The category
is explicit in each README; use `--self-test` to verify mixing is detected.
Run `--smoke` with Pillow and the configured headless frontend to assert
audio renders a blank display and a sprite graphics sample is visible.

Use `pce-development/examples/` for project recipes; each recipe identifies
where SDK-specific adaptation is required. Scratch projects copy the starter
Makefile and tools, then select the LLVM-MOS driver for the requested HuCard or
CD target. The shared PCE image/font/sprite converters, audio encoders, BIOS
ADPCM player, and SoftADPCM/DDA decoder library are documented in
`pce-development/tools/pce/README.md`. These tools contain no game-specific
art, ROM, BIOS, or archive data.

## Offline game-request router (for Luna / Leading Edge / smaller local models)

Before inventing a new game/physics scaffold, run `python3 pce-development/workflows/offline.py route "USER REQUEST"` and follow its concrete recipe. For a simple playable platformer choose example 26; for explicit platformer + racing segments choose example 27 with its generated `hybrid_rules.h`. Read `pce-development/workflows/README.md` and the generated project's README. Do not mix their stage-specific X/Y coordinates, and do not treat host-side simulation as game execution. Enforce one scene owner at a time, and test entry and return transitions. `make test` runs offline unit/static checks; `make hybrid-test` needs a newer RPC-capable emulator. **Never claim a failing P2TR scenario succeeded on a prebuilt emulator without `trace_frames`.**

The user-provided transcripts are private inputs for deriving incident patterns only; they are not part of the redistributable toolkit. A separate `transcript_lessons.py` reports aggregate categories without copying their text. Keep them outside commits and published archives.

## Additional Luna / local-AI failure gates

Four later sessions exposed hallucinated joypad/sprite API names, hand-counted array overruns, linker/vector overflows, GUI emulator timeouts mistaken for gameplay success, and .pce builds mistaken for a Super CD disc. **Before writing a large game**, follow `pce-development/references/local-ai-transcript-fixes.md`, run `offline.py route` with the complete user request, then use the new `model_guard.py scan` and `assetpack.py --check` commands. In existing game starters `make model-check` runs before the build. `make diagnose LOG=...` maps common errors to actions; `make acceptance-check` deliberately fails until distinct evidence exists. For a JSON tilemap to real 4bpp VDC graphics, use standalone `examples/28-generated-level`. Do not claim that its entity metadata is playable enemies. Use `make agent-check agent-assets agent-build` at the root.

## Cross-genre P2TR/G2TR and visual-novel work

Never reuse `P2TR v1` collision-surface fields for unrelated genres. Keep platformer P2TR v1 (216 bytes ×2); use the new `G2TR v2` (64 bytes ×2) and genre-specific validators for shmup, racing, raycaster or visual novel. Run `make genre-check` first (no SDK), then `make genre-build`, `PCE_HEADLESS=... make genre-test` when RPC and compiler exist. `trace_frames` in the bundled emulator only accepts P2TR v1; the generic runner uses `run`+`memread` instead. A RAM trace is game-authored data, not evidence of pixel output.

For visual novels, do not hand-code huge picture arrays: use `examples/29-visual-novel/tools/vn_pack.py` and versioned PNGs. Single-palette generator only requires Pillow; multi-palette fitter requires NumPy too. Use generated BAT/4bpp patterns for background and SAT 16x16 pattern indices for mouth overlays. Check the manifest for ROM/VRAM/palette constraints and `make visual-test` for actual mouth-only screenshot differences. Avoid making a visual-novel sprite depend on sound/text raster init unless requested.

## Rendered genre examples and screenshot acceptance (33–35)

After choosing a genre with `offline.py route`, prefer rendered example 33
(shmup), 34 (raycaster), or 35 (conventional racer) when visual output is part
of the request. Preserve examples 30–32 as intentionally **nonvisual** G2TR
instrumentation probes. For true 512×224 pseudo-bitmap road rendering, use
micro example 86 rather than calling the fixed perspective racer Mode 7.

For 33 and 35, change PNGs and run `make assets` instead of hand-writing huge
C graphics arrays. `tools/scene_pack.py` validates indexed colours, a 64×16
sprite strip, tile counts and VRAM allocation. For 34, raycast actual map cells
and submit the height columns to the VDC BAT; do not substitute a static image
and claim that it is a raycaster.

Run `make trace` **and** `make visual-test` for each rendered project. The first
checks game-authored G2TR telemetry under scripted input; the second captures
and compares actual emulator pixels, input latching and screen-space motion.
Neither proves physical hardware performance, audio or complete game mechanics.
The basic `pce_joypad_read()` returns **eight bits** (two-button controls); do
not invert it into `uint16_t` and interpret the high nibble as extra buttons.
Initialize mutable gameplay globals explicitly in `main()` for minimal HuCard
startup environments; do not assume initialized `.data` was copied as on a PC.
See `pce-development/tools/pce/GENRE_TRACE.md` for the trace contract.
