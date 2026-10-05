# Headless emulator and MCP debugging

For LLVM-MOS `PATH` bootstrap and terminal instructions for a missing CD BIOS,
see the [toolchain setup guide](toolchain-setup.md).

This bundle includes a source-only Mednafen PCE Dev checkout at
[`third_party/mednafenPceDev-main/`](../third_party/mednafenPceDev-main/). Its
[`README_HEADLESS.md`](../third_party/mednafenPceDev-main/README_HEADLESS.md)
documents the headless build, binary options, and MCP server. The source tree
also contains [`build_headless.sh`](../third_party/mednafenPceDev-main/build_headless.sh)
and the [`MCP wrapper`](../third_party/mednafenPceDev-main/mednafen/src/drivers_libxxx/mcp_server.py).
The bundle has no compiled emulator binary, game ROM/disc image, or BIOS.
Discover project-specific executable and BIOS paths; do not assume a private
BIOS filename or prior conversation log.

## Find the real configuration

1. Read the active project's emulator notes and inspect its configured binary
   path. If no binary is supplied, use the bundled `README_HEADLESS.md` and
   `build_headless.sh` to build this source snapshot.
2. Run the selected binary's `--help` and confirm it matches the bundled source
   or the active project's documented build and supports the operations needed.
3. Use the extracted System Card `.pce` path supplied/configured by the user.
   Do not assume it is included in the repository. Never copy BIOS firmware to
   a public skill or project bundle. Run `make bios-check` in projects using
   the starter Makefile. If no BIOS path is configured, it tells the terminal
   to place the file in `${XDG_DATA_HOME:-$HOME/.local/share}/pce-development/bios`
   and set `PCE_SYSTEM_CARD_BIOS` to the full file path. Do not search unrelated
   folders.
4. Inspect the MCP server's live tool list before using it. Clients vary in
   their MCP configuration schema and not every server exposes the same tools.
5. Set isolated base/config/save and output directories for reproducibility.

## Run the bundled headless build

`<skill-root>` below means the installed directory containing `SKILL.md`.
Resolve it from the active skill's loaded file path; it is not the project's
working directory.

```sh
cd "<skill-root>/third_party/mednafenPceDev-main"
./build_headless.sh
```

The documented output is `mednafen/src/mednafen-pce-headless` beneath that
checkout. Read `README_HEADLESS.md` for its exact CLI options and examples. For
an already installed or differently built binary, run its `--help` rather
than assuming these flags match. Supply the disc, the user's extracted System
Card BIOS when needed, an isolated writable directory, a bounded run, and
requested capture outputs. CD emulation needs a System Card image in the format
the selected binary expects, not a compressed archive. Record the firmware
version used, but do not copy the firmware itself.

The bundled build script compiles the source and copies the headless frontend
to the documented output path. A project-installed binary may be a different
revision; record which binary was actually used.

## MCP setup and operations

The bundled wrapper accepts these startup arguments; replace every bracketed
path with the active file/directory:

```sh
python3 "<skill-root>/third_party/mednafenPceDev-main/mednafen/src/drivers_libxxx/mcp_server.py" \
  --binary "<headless-binary>" \
  --rom "<disc-image>" \
  --bios "<user-supplied-system-card.pce>" \
  --base-dir "<isolated-base-dir>" \
  --output-dir "<capture-dir>"
```

These arguments are confirmed by the bundled wrapper's parser. If using another
wrapper, read its startup help and the MCP client's own stdio-server schema.
Keep MCP JSON-RPC on stdio and diagnostics on stderr. The bundled wrapper
exposes `run_frames`, `disassemble`, `read_memory`, `take_screenshot`,
`coverage_clear`, `coverage_dump`, `start_y4m_recording`,
`stop_y4m_recording`, `reset`, and `status`. Confirm the live `tools/list`
before use, especially when a project supplies another wrapper.

For a given run:

1. Build the image under test and identify the current output path/revision.
2. Start the MCP server with a fresh base directory and explicit BIOS/disc.
3. Run a bounded frame count; inspect `status` and capture a screenshot.
4. Disassemble the active PC with the current logical MPR map. Pair logical
   memory/coverage with bank/MPR observations for banked execution windows.
5. Read memory/coverage around the relevant state transition.
6. If input or memory seeding is needed, use a project test harness; confirm it
   exercises the game's native update/draw/loader path.

## Tool limits to check

- The MCP server may have no controller-input or memory-write tool. A title
  reaching gameplay by itself does not prove a requested input path.
- Logical-PC coverage can alias different physical banks at the same CPU
  address. Record active MPR/bank while interpreting it.
- A side-effect-free memory read does not exercise hardware I/O writes.
- Video-only Y4M has no audio evidence.
- Emulator success does not prove physical CD drive, System Card, Arcade Card,
  or console-timing behavior.

For a screenshot request, pass the returned image to the multimodal model with
the source and asset manifest. For boot failures, inspect BIOS/version, disc
extents, IPL entry, MPR state, and application disassembly in that order.
See [`examples/13-headless-debugging/README.md`](../examples/13-headless-debugging/README.md)
for a worked workflow.
