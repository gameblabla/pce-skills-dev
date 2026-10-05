---
name: pce-development
description: >-
  Develop, debug, profile, or verify PC Engine and TurboGrafx-16 software built
  with LLVM-MOS for CD-ROM² and Arcade Card hardware. Includes standalone
  project recipes, code-bank safety guidance, and headless emulator workflows.
---

# PC Engine and TurboGrafx-16 development

Use this skill for projects built with the LLVM-MOS PCE CD target for PC Engine
hardware: VDC, VCE, PSG, CD-ROM², and Arcade Card software, assets, builds,
debugging, and emulator verification. HuC6280 names the console CPU and its
instruction set; LLVM-MOS is the only supported compiler/assembler toolchain
here. This skill works without any game's source tree, conversation export, or
private BIOS file. Its examples define portable patterns for the active
LLVM-MOS PCE CD SDK and linker.

Start from the current project tree. Inspect its instructions, status, build
system, code, and hardware target before applying an example. Preserve existing
changes. Do not assume a game's source or exported conversation logs are
available. The guides and examples under this skill contain their own
reasoning. Build and assemble all code with LLVM-MOS for PCE CD. Never stash,
reset, restore, or overwrite unrelated user edits to make a build convenient.

Use the live source, linker script, build files, generated reports, and current
ELF/map files for facts that can change, especially bank placement, free RAM,
tile use, and performance. Historical notes and screenshots explain why a
design exists, but may describe an earlier revision. Cross-check them against
the current code before repeating their numbers or assumptions.

## Route to the relevant guide

- For CPU banking, overlays, memory budgets, display limits, or raster timing,
  read [hardware and architecture](references/hardware-and-architecture.md) and
  [bank placement and safe relocation](references/banks-and-overlays.md).
- For game feature changes, sprite/background production, or audio, read
  [runtime and asset pipeline](references/runtime-and-assets.md) and the
  [CD-ROM² project cookbook](references/project-cookbook.md).
- For a platformer that combines collision, scrolling, sprites, and a fixed HUD,
  read the [platformer integration example](examples/25-platformer-integration/README.md)
  alongside examples 08, 17, 18, and 21. Those smaller samples are not a
  complete game scaffold when combined without their stated limits.
- For platformer physics invariants, text-only per-frame state traces, and
  repeatable input scenarios, read [platformer rules](references/platformer-rules.md).
- For symptom tracing, test selection, profiling, and hardware claims, read
  [debugging and verification](references/debugging-and-verification.md) and
  the [headless emulator and MCP guide](references/headless-emulator.md).
- For screenshots, video, or vague requests about what looks misplaced, read
  [visual debugging](references/visual-debugging.md) and trace the same frame
  through its source layout, camera/scroll, renderer, and display publication.
- For lessons from recurring regressions and measured fixes, read
  [incident patterns](references/incident-patterns.md).
- For scratch projects and worked starter patterns, use the self-contained
  [examples folder](examples/README.md). Code there is marked as pseudocode
  whenever it needs adaptation to a project's SDK.
- For reusable host converters, audio encoders, or the CD hardware and
  SoftADPCM players, read the [shared PCE tools guide](tools/pce/README.md).
- For a new project's Makefile, automatic LLVM-MOS SDK setup, or missing BIOS
  path guidance, use the [toolchain setup reference](references/toolchain-setup.md)
  and copy the shared files under [examples/starter](examples/starter/).

## Working method

Trace a requested change end to end: player/input or source-game state, source
data/export, host-side bake, runtime loader, renderer/audio path, and observable
result. A visual or audio defect may originate in a baked asset, shared palette,
cache lifetime, bank overlay, transfer timing, or test fixture rather than in
the final drawing call.

Before proposing code-shaped fixes, confirm the current symbol names, ownership,
and call order in source. Label sketches as pseudocode when they are not
drop-in code; do not introduce flags, bank mappings, or register operations
without tracing who consumes them and when.

Use Python for every arithmetic calculation, including byte totals, bank
headroom, address ranges, fixed-point conversions, sprite budgets, and cycle
budgets. Run `python3 scripts/calc.py 'EXPRESSION'` for numeric work and
`python3 scripts/bank_space.py PATH/TO/runtime.json` to rank linker-reported
bank headroom. The bank helper reports capacity only; it does not decide that
a bank is safe to reuse. Follow the bank-relocation guide before moving code.
When Python output is already supplied, cite that result without repeating or
re-evaluating its input expression. If a calculation tool is unavailable,
defer exact values and state the helper command needed.
Use Python for visual pixel offsets and coordinate conversions too. Do not
make numeric comparisons or estimates mentally, including approximate ranges
and “available bytes versus required bytes.” If a tool is unavailable, report
the qualitative direction only and identify the calculation still needed.
Do not invent numeric limits, burst sizes, pixel offsets, or sample values when
neither source nor Python output supplies them.

Keep adaptations native to the hardware and LLVM-MOS PCE CD target. The Arcade Card adds memory and data
ports; it does not add another background plane, general-purpose scaling,
blending, or sound voices. Prefer palette animation, pre-baked poses and sizes,
background pattern animation, selective sprites, and scanline scrolling where
they fit the design. Read the relevant guide before choosing a technique.

For a code change, build the PCE image with that project's pinned LLVM-MOS PCE
CD toolchain and choose a focused regression check for the changed path. Use
the active project’s full test target when shared behavior is affected. State
exactly which checks ran. Emulator checks, manually viewed emulator
captures, a human playthrough, and physical PC Engine tests are different
evidence; never report one as another.

For a new example or scratch project, copy the starter Makefile and its tools,
then use `make run` or `make debug` for neutral-input capture and coverage. Use
`make trace` with a P2TR-instrumented game and an explicit scenario file for
repeatable platformer input and text diagnostics. Treat those Make targets as
the only project interface to the emulator; do not search for or invoke an
emulator executable from a coding-agent prompt. The helpers use the configured
headless binary and keep its command line out of the game-development workflow.

Before calling a build a Super CD-ROM² game, verify the produced artifact and
boot path. A direct `mos-pce-clang` build of a `.pce` ROM is the HuCard preview
path used by most examples here. A CD-ROM² target needs the CD compiler and the
project's IPL/disc-image packaging flow, plus a user-supplied compatible System
Card BIOS for emulator boot. Do not infer the target from a Makefile comment,
the output filename, or a successful HuCard emulator run. Follow
[`examples/25-platformer-integration/README.md`](examples/25-platformer-integration/README.md)
for the output audit.

## Local references and project-specific facts

This public skill bundle includes no game source tree, exported conversation
logs, compiled emulator binary, ROM/disc image, or BIOS image. It includes a
licensed PCE headless source snapshot under `third_party/`; use the project's
Make targets to select or build it. Do not ask a coding agent to locate, name,
or invoke an emulator executable directly. The skill's run/debug/trace helpers
own that detail. If the active project supplies a different headless build,
configure it through `PCE_HEADLESS`.
If the user supplies a project/base-code checkout, treat that checkout as the
project-specific authority. Do not invent an API, bank assignment, build
command, BIOS filename, or measured timing value when the relevant source does
not supply it.

For local evaluation, run `python3 scripts/eval_local_ai.py` from this skill's
directory. Read `scripts/README.md` for endpoint, multimodal, and score details.

The [LLVM-MOS PCE target documentation](https://llvm-mos.org/wiki/PCE_target)
defines target ABI and linker conventions. Use the
[LLVM-MOS assembler documentation](https://llvm-mos.org/wiki/Assembler) for
assembly syntax. Consult PCE hardware references for CPU/VDC/Arcade Card
behavior, then confirm instruction support, calling convention, and generated
code with the installed LLVM-MOS target. Project linker scripts, SDK headers,
drivers, and tests are authoritative for the active build.
