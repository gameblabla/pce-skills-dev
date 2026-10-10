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
