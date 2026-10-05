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
Use `pce-development/examples/` for project recipes; each recipe identifies
where SDK-specific adaptation is required. Scratch projects copy the starter
Makefile and tools, then select the LLVM-MOS driver for the requested HuCard or
CD target. The shared PCE image/font/sprite converters, audio encoders, BIOS
ADPCM player, and SoftADPCM/DDA decoder library are documented in
`pce-development/tools/pce/README.md`. These tools contain no game-specific
art, ROM, BIOS, or archive data.
