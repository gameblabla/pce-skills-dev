# PC Engine development skill bundle

Start with [`pce-development/SKILL.md`](pce-development/SKILL.md). The skill
and its examples are self-contained: do not assume a sibling game repository,
private BIOS, compiled emulator binary, or exported conversation logs are
present. A source-only Mednafen PCE Dev checkout, headless build guide, and MCP
wrapper are vendored under `pce-development/third_party/`; preserve its
upstream and component license notices. Discover project-specific binary,
memory, BIOS, and emulator paths from the active project or ask for missing
SDK-specific information when it blocks a safe implementation.

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
Use `pce-development/examples/` for project recipes; every recipe states where
SDK-specific adaptation is required. Scratch projects copy the starter
Makefile/bootstrap and use only the LLVM-MOS `mos-pce-clang` driver; if no
compiler is on PATH, the helper installs SDK 23.2.0 user-locally.
`make bios-check` prints the user-local placement folder when CD firmware is
absent.

The shared PCE image/font/sprite converters, audio encoders, BIOS ADPCM player,
and SoftADPCM/DDA decoder library are documented in
`pce-development/tools/pce/README.md`. These tools are standalone and carry no
Saber Rider art, ROM, BIOS, or game-specific archive data.
