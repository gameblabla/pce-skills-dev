# Debugging and verification

Connect one reported symptom to a reproducible state, trace the responsible
source/data/hardware path, and verify at the level the claim requires. The
skill's guidance and examples stand alone; do not depend on previous chat logs
or a private project history.

## Reproduce before editing

1. Record the current revision and dirty files. Preserve unrelated edits.
2. Record the build identity, LLVM-MOS version/flags, disc image, BIOS version
   and emulator configuration used for the reproduction.
3. Match scene, mode, input, timing, save state, and other setup. Prefer a
   freshly rebuilt image. Confirm the emulator loaded that image and reached
   the intended application state rather than remaining in the BIOS.
4. Trace the symptom through source state, generated assets, CD/archive
   loading, bank/MPR mapping, renderer/audio path, hardware register writes,
   and VBlank/HBlank timing as relevant.
5. Add the smallest probe or assertion that distinguishes likely causes. Keep
   a failing-before/fixed-after test where practical.

For a visual symptom, compare the same scene/state/frame and inspect source
coordinates, camera/scroll, active mode, manifest and cache lifetime. For
audio, capture the isolated output and simultaneous music/raster case. For a
raster glitch, measure IRQ timing and VDC writes rather than relying on a
static screenshot.

## Build and focused test

Use the project's pinned LLVM-MOS `mos-pce-clang` toolchain and matching
headers, assembler, linker scripts, libraries, and disc tools. Build with its
documented command and confirm the output image, map/ELF, memory report, asset
manifest, and disc extents were regenerated. Never report success from a stale
artifact or from a command whose status was not checked.

Run the narrowest regression that exercises the edited path, then broaden
coverage when shared banking, loader, video, audio, or interrupt behavior is
affected. If the project has no automated test for the path, write down the
manual setup/capture and the exact assertion that was checked. Do not run or
claim a full test suite unless the full command completes successfully.

## Evidence labels

- **Build passed**: the stated LLVM-MOS build command completed for the named
  source revision and output.
- **Automated emulator test passed**: a named executable check passed with the
  stated inputs/seed and assertions.
- **Emulator image/audio reviewed**: the named rebuilt image/output was
  inspected; state whether the comparison was manual or machine-assisted.
- **Manual emulator playthrough**: the flow was played without forcing
  intermediate game state through a harness.
- **Physical hardware tested**: the stated console, System Card/CD setup, and
  any Arcade Card/media were actually exercised.

An accurate emulator does not prove physical disc behavior or timing. A seeded
scenario proves only the path its seed executes. State the exact stage/scene,
frame count, inputs, forced state, output artifact, and assertions. Name tests
that did not run and behavior that remains unknown.

## Visual and multimodal checks

Pass screenshots/videos to an image-capable model with the relevant source
snippet in the same request. If the local endpoint is text-only, say that no
image inspection occurred. Use Python for measurements such as pixel bounds,
displacement, colors, tile totals, and frame counts. Similarity metrics do not
prove collision, input handling, bank mapping, or timing.

See [visual debugging](visual-debugging.md), the standalone HUD request in
[`examples/11-visual-request.md`](../examples/11-visual-request.md), and the
[headless/MCP example](../examples/13-headless-debugging.md).
