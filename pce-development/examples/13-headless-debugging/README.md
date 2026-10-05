# Example 13: headless emulator and MCP debugging

![Example 13: headless emulator and MCP debugging emulator screenshot](assets/screenshot.png)

**Project:** Run `make` in this folder to build `build/13-headless-debugging.pce` with the bundled LLVM-MOS setup. This HuCard ROM can run in a PC Engine emulator. CD-ROM² deployment needs project-specific IPL/disc packaging and a user-supplied System Card BIOS.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable source artwork. `assets/screenshot.png` is captured from the built ROM in the headless emulator. See additional files in this folder for topic-specific data.

The public skill bundles a source-only Mednafen PCE Dev checkout at
[`../third_party/mednafenPceDev-main/`](../../third_party/mednafenPceDev-main/),
including its headless MCP server and
[`README_HEADLESS.md`](../../third_party/mednafenPceDev-main/README_HEADLESS.md).
It does not include a compiled binary, game ROM/disc, or BIOS. Use a binary
configured by the project or build the bundled source. Never include a private
BIOS image in a public skill bundle.

## Discover the actual tools

1. Read the active project's emulator instructions and check its configured
   executable path/environment variable.
2. If no binary is available, follow the bundled `README_HEADLESS.md` and run
   `build_headless.sh` from the vendored source directory. Resolve
   `<skill-root>` from the loaded skill's `SKILL.md` location; it is separate
   from the active project's working directory. Its output is
   `mednafen/src/mednafen-pce-headless` inside that checkout. Otherwise run the
   configured binary's `--help`; do not assume it is beside its source.
3. Run `make bios-check`. If no System Card path is configured, the target
   creates and prints `${XDG_DATA_HOME:-$HOME/.local/share}/pce-development/bios`
   in the terminal, then explains how to set `PCE_SYSTEM_CARD_BIOS` to the
   extracted `.pce` file. Do not assume a filename or search unrelated
   directories.
4. Inspect the MCP server's `tools/list` response and use only tools it
   actually exposes.
5. Isolate its base/config/save directory and its screenshot/video output for
   this run.

## Headless CLI and MCP startup

```sh
"<headless-binary>" --help
```

When using the bundled build, follow its `README_HEADLESS.md` for confirmed
CLI examples (`--rom`, `--frames`, `--screenshot`, `--cov`, and CD `--bios`).
The `--help` output for the active executable remains authoritative if it is a
different build. The BIOS must be a user-supplied extracted System Card image;
do not assume its filename. Record its name/version in the test report without
copying the firmware.

## MCP debugging sequence

Launch the bundled server with its own documented startup arguments (the MCP
client's registration schema still varies):

```sh
python3 "<skill-root>/third_party/mednafenPceDev-main/mednafen/src/drivers_libxxx/mcp_server.py" \
  --binary "<headless-binary>" --rom "<disc-image>" \
  --bios "<user-supplied-system-card.pce>" \
  --base-dir "<isolated-base-dir>" --output-dir "<capture-dir>"
```

Do not pass a private BIOS or disc path from another machine. If a project
supplies a different wrapper, inspect that wrapper's parser and the MCP
client's documented registration schema.

The Mednafen headless MCP wrapper examined for these recipes offers tools for
running frames, reading status, disassembling, reading logical/physical memory,
taking a screenshot, clearing/dumping logical-PC coverage, recording Y4M, and
resetting. Check the live tool list: other wrappers may differ.

Run a bounded interval using the project's configured frame/time limit, inspect
status and the screenshot, then disassemble the active PC with the correct MPR
mapping. Use logical/physical memory reads to compare loaded code/data. Capture
coverage around a specific scenario, not the entire boot if the question is
whether one function ran.

## Limits and follow-up

- The referenced MCP wrapper does not provide controller input or arbitrary
  memory writes. Use a project test harness or extend a local test adapter if
  a seeded gameplay state is required.
- Coverage counts logical 16-bit PCs, so separate physical banks at the same
  logical window may alias. Record the active MPR/bank alongside coverage.
- Read-only memory inspection does not test I/O side effects.
- Y4M output is video-only in this headless build; it is not audio evidence.
- Emulator success is not physical CD drive, System Card, Arcade Card, or
  console-timing proof.

For a visual request, pass the MCP screenshot image to the local model together
with the responsible source and generated-asset manifest. For a boot failure,
inspect BIOS/version, disc extent, IPL entry, MPR state, then application
disassembly in that order.
