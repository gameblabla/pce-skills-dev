# mednafenPceDev headless PCE build

This tree adds a no-SDL PC Engine frontend using Mednafen's existing `--enable-libxxx-mode` build path.
The frontend lives in `mednafen/src/drivers_libxxx/main.cpp` and supports batch CLI operation plus a persistent control channel used by the bundled MCP server.

## Capabilities

- Headless PC Engine / TurboGrafx-16 emulation with no SDL runtime dependency.
- HuC6280 disassembly through the existing PCE debugger/disassembler.
- Logical-PC execution coverage with per-address hit counts.
- Side-effect-free logical or physical memory reads.
- PNG screenshots from the rendered Mednafen surface.
- YUV4MPEG2 (`.y4m`) video recording, YUV 4:4:4, at the core-reported frame rate.
- Persistent stdio control mode (`--rpc`) for automation.
- MCP stdio server exposing run/disasm/memory/coverage/screenshot/Y4M/reset/status tools.

Coverage is logical 16-bit PC coverage. Disassembly uses the current HuC6280 MPR mapping at the moment the request is made.

## Build on Linux

From the repository root:

```sh
./build_headless.sh
```

The result is copied to:

```text
mednafen/src/mednafen-pce-headless
```

The headless build deliberately does not link SDL. It still uses the normal Mednafen core dependencies such as zlib and the C/C++ runtime.

## CLI examples

Run 120 frames, save a PNG, Y4M recording, and coverage JSON:

```sh
mednafen/src/mednafen-pce-headless \
  --rom game.pce \
  --frames 120 \
  --screenshot frame.png \
  --y4m capture.y4m \
  --cov coverage.json
```

ZIP-contained HuCard ROMs are accepted by the normal Mednafen archive loader:

```sh
mednafen/src/mednafen-pce-headless --rom game.zip --frames 60
```

Disassemble 32 instructions at logical address `$E000` after running one frame:

```sh
mednafen/src/mednafen-pce-headless --rom game.pce --frames 1 --disasm 0xE000:32
```

For PC Engine CD images, `--bios FILE` sets `pce.cdbios`. Pass the extracted System Card `.pce` firmware file rather than a ZIP archive.

## Native persistent control channel

Start with `--rpc`. Commands are one line each, tab separated; replies are one JSON object per line.

```text
status
run\t60
disasm\t0xE000\t16
memread\t0x2000\t32\t1
screenshot\t/tmp/frame.png
cov_clear
cov_dump\t/tmp/cov.json
record_start\t/tmp/capture.y4m
record_stop
reset
quit
```

Paths sent over the control channel are URL/percent-decoded, which is how the MCP wrapper safely passes paths containing spaces.

## MCP server

`mednafen/src/drivers_libxxx/mcp_server.py` is a standard-library-only MCP stdio server. It starts one native emulator instance and keeps its state alive across tool calls.

Example:

```sh
python3 mednafen/src/drivers_libxxx/mcp_server.py \
  --binary mednafen/src/mednafen-pce-headless \
  --rom game.pce \
  --base-dir .mednafen-headless \
  --output-dir ./captures
```

Exposed MCP tools:

- `run_frames`
- `disassemble`
- `read_memory`
- `take_screenshot` (returns PNG image content as well as a path)
- `coverage_clear`
- `coverage_dump`
- `start_y4m_recording`
- `stop_y4m_recording`
- `reset`
- `status`

## Notes

Y4M is video-only by design. Audio emulation output is disabled in this frontend. The native PNG writer preserves Mednafen's per-scanline PCE width information; Y4M is scaled to the core's nominal fixed output dimensions so every frame has the same size.
