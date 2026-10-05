# Headless PC Engine frontend

This source tree adds a no-SDL PC Engine frontend with bounded batch runs and
a persistent control channel. The control channel supports input, screenshots,
memory inspection, execution coverage, and video recording. The MCP wrapper
adds the same operations for clients that already have an MCP host configured.

## Build on Linux

From this source tree's root:

```sh
./build_headless.sh
```

The build script places the resulting executable at `pce-headless` in this
directory. It requires the normal core dependencies, including zlib and the C/C++
runtime, and does not link SDL.

## Bounded command-line run

```sh
./pce-headless --rom game.pce --frames 120 --screenshot build/frame.png \
  --y4m build/capture.y4m --cov build/coverage.json --base-dir build/base
```

For CD images, pass the user's extracted System Card file with `--bios FILE`.
Do not bundle BIOS firmware with this skill. The executable's `--help` output
is authoritative if this build has been replaced or configured differently.

## Persistent control channel

Start with `--rpc`; send one tab-delimited request and receive one JSON reply per
line. The channel is intended for the project helper or an already-configured
MCP host, not as an emulator command copied into a game prompt.

```text
status
input<TAB>mask
run<TAB>60
trace_frames<TAB>address<TAB>length<TAB>frames
memread<TAB>address<TAB>length<TAB>logical
disasm<TAB>address<TAB>count
screenshot<TAB>/tmp/frame.png
cov_clear
cov_dump<TAB>/tmp/coverage.json
record_start<TAB>/tmp/capture.y4m
record_stop
reset
quit
```

`input` sets a PCE active-high button mask: I, II, Select, Run, Up, Right,
Down, Left, III, IV, V, and VI occupy bits 0-11. `trace_frames` accepts the
logical RAM address of two consecutive P2TR v1 records and chooses the newest
complete 216-byte record after each publication. Writers alternate the records,
marking the inactive record's `reserved` odd while fields are changing and
publishing its next even sequence after completion. The prior active record
stays intact during the write, so a VBlank boundary cannot expose a partial
sample. The request accepts up to 3,600 game-frame samples. See the skill's
`references/platformer-rules.md` for its layout and diagnostics.

## MCP integration

The standard-library-only MCP server is in the source tree's Python frontend
directory. A host-configured instance exposes `run_frames`, `run_platformer_scenario`,
`disassemble`, `read_memory`, `take_screenshot`, coverage, Y4M recording, `reset`,
and `status`. Inspect `tools/list` on the live server because client wrappers
can vary. The project Make target `trace` is the standalone alternative when
MCP has not been configured.

Coverage is logical-PC coverage and can alias code in different banks mapped at
the same address. Disassembly uses the current HuC6280 MPR mapping. PNG preserves
per-scanline PCE width information; Y4M is video-only and scales to the core's
nominal fixed output dimensions. Emulator results do not prove physical-console
timing.
