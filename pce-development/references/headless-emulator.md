# Headless emulator and MCP debugging

For LLVM-MOS bootstrap and a missing CD System Card path, read the
[toolchain setup guide](toolchain-setup.md). For platformer physics, read
[platformer rules](platformer-rules.md).

## Use the project interface

From a copied starter project, use:

```sh
make run
make debug
```

These Make targets choose the workspace-configured headless PCE binary, use an
isolated base directory, and print the screenshot and optional coverage paths.
They intentionally hide the executable name and command line so a coding agent
can work through project targets. Configure another build with `PCE_HEADLESS`
if the active project requires it. Keep any direct frontend commands inside
the helper scripts; do not put executable names or manual emulator launch
instructions into game tasks given to a local coding agent.

`make run` captures a neutral-input frame after the requested frame count.
`make debug` also captures logical-PC execution coverage and can disassemble an
address passed with `PCE_DEBUG_DISASM`. Neither target simulates gameplay input.
For walking, jumping, landing, enemies, or a goal, use a deterministic test
scenario instead of treating neutral frames as gameplay evidence.

For a platformer with a P2TR v1 trace record, copy the starter helpers and use:

```sh
make trace
```

By default, the helper reads the trace symbol address from the current ELF and
uses `tools/platformer-scenario.example.json`. Point the symbol at two
consecutive P2TR records; the helper reads the full 432-byte window and chooses
the newest complete record. Alternate buffers, setting each low `reserved` byte
odd while writing and to its next even value after the record is complete.
Override `PCE_PLATFORM_TRACE_ADDRESS` only if the project cannot emit an ELF;
set `PCE_PLATFORM_TRACE_INITIAL_FRAMES` when the game publishes its record later
during boot; use `PCE_PLATFORM_TRACE_SCENARIO` to select another JSON array of
`{ "frames": N, "buttons": [] }` segments. Button names are `i`, `ii`,
`select`, `run`, `up`, `right`, `down`, `left`, `iii`, `iv`, `v`, and `vi`.
Each set is held for its segment, so a tap uses a one-frame segment followed by
a release segment. The helper writes a compact JSON physics report to
`build/platformer-trace.json` by default. It samples a complete 216-byte
game-authored record after each publication and identifies
missed landings, unsupported grounded states, stalled gravity/movement, art to
collision geometry mismatches, and camera/sprite coordinate mismatches. Each
input segment also reports the button mask actually observed by the game and
how many trace samples elapsed before that mask appeared; align frame-specific
movement and jump claims to the observed mask.

The trace helper runs up to 3,600 frames per invocation. Keep individual probes
short and isolate title entry, idle fall, walk, jump, landing, scroll, enemy,
and goal behaviors. Reset or load a known state before comparing runs. Always
report the exact scenario, game-frame range, and emulator-frame range. Read the
`event_samples` section for frame-addressed jump, landing, death, respawn, and
goal events. If the game frame repeats or jumps between emulator samples, check
the VBlank sampling phase and trace publication point before calling it a physics
failure.

For CD, `PCE_RUN_IMAGE` must name the project's packaged disc image, and
`PCE_SYSTEM_CARD_BIOS` must name a user-supplied extracted System Card image.
An application `.bin` is not a bootable disc. `make bios-check` prints the
user-local firmware folder when no image is configured; do not search unrelated
folders or copy firmware into the skill.

## MCP tools

If the host has already configured the bundled PCE MCP server, inspect its live
`tools/list` response before use. Available tools vary by host and revision.
The current wrapper provides bounded frame runs, disassembly, logical/physical
memory reads, screenshots, coverage, Y4M recording, reset, and status. It also
provides `run_platformer_scenario`, which accepts an input script and the trace
record's logical RAM address, then returns frame-addressed text diagnostics.
Use the MCP scenario tool when present; otherwise `make trace` provides the
same test path without configuring MCP.

MCP protocol uses stdio for JSON-RPC; keep diagnostics on stderr. The trace
tool's button masks are active-high PCE bits 0-11: I, II, Select, Run, Up,
Right, Down, Left, III, IV, V, VI. Its report is derived from game-authored
data and cannot verify raster output, palette appearance, or physical hardware
timing. Use `take_screenshot` for a visual artifact and label what a text-only
reviewer cannot establish.

## Evidence limits

- Logical-PC coverage may alias code at the same logical address in different
  mapped banks; record the active MPR/bank when analyzing coverage.
- A side-effect-free memory read does not test hardware I/O writes.
- Y4M output is video-only; it is not audio evidence.
- Emulator success does not prove physical CD drive, System Card, Arcade Card,
  or console-timing behavior.
- A P2TR report can establish the recorded game state and identify internal
  inconsistencies. It cannot prove that the visible screenshot matches those
  fields; compare source submission, screenshot, and record when they disagree.
