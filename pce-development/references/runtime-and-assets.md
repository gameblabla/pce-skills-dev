# Runtime and asset pipeline

Trace each feature from the source asset or gameplay state through the host
baker, disc extent, runtime loader, CPU/Arcade memory, and final hardware output.
This guide is toolchain-specific at the build boundary: compile for LLVM-MOS
PCE CD with one pinned SDK/toolchain set. Adapter and asset-generator names
below are conceptual; use the active project symbols.

## Source-to-screen trace

For a visual feature, identify:

1. Authored image/map/animation and its color/anchor conventions.
2. Export format and deterministic host-side conversion.
3. Generated manifest: semantic names, dimensions, palettes, source ranges,
   checksums, frame descriptors, and memory budget.
4. CD image extent/track placement and runtime lookup method.
5. Loader destination: CPU RAM, a mapped bank, Arcade RAM, VRAM, or another
   hardware buffer.
6. Runtime cache ownership, VBlank publication, and release point.
7. SAT/BAT/VDC state that produces the displayed result.

If the image looks wrong while runtime coordinates appear reasonable, inspect
the generated representation, sprite sheet binding, palette, transparency,
manifest IDs, and cache lifetime before changing placement.

For sound, follow source sample -> host encoding -> manifest/table -> CD or
resident memory -> BIOS ADPCM, PSG DDA, or CD-DA path. Confirm playback
ownership and concurrent disc-read policy.

## Asset pipeline rules

- Keep authored source and generated outputs separate.
- Make conversion deterministic and include a source hash/manifest.
- Identify sprites by names/semantic records; raw numeric IDs can move when
  another strip is inserted.
- Generate host previews from the emitted target patterns/palettes.
- Review every character/weapon/frame variant when a shared exporter loop
  changes.
- Budget cache peaks and transfer bytes, not just unique asset count. Include
  content still visible until VBlank.
- Use Python helpers for all byte, tile, color-count, sector, and frame-budget
  calculations.

## Runtime ownership

Assign each memory area one documented owner and lifetime: code overlay,
constants/tables, main working state, CD staging window, Arcade archive,
decompression scratch, audio data, or VRAM allocation. Verify that two
subsystems don't borrow the same bank/window concurrently. Section placement
and linker-reported free space alone do not prove runtime availability.

Keep global state transitions small. A loader should report failure and leave
the previous screen or a deliberate error screen intact; it should not expose
half-loaded assets. Publish a new scene only after its required graphics,
palette, map, and SAT/BAT references are ready.

## Audio pipeline rules

- Use the lowest-complexity sound path that meets the content and concurrency
  need: PSG tone/noise, PSG DDA, BIOS ADPCM, or CD-DA.
- Keep event tables semantic, with explicit sample lengths, source banks,
  loop boundaries, and any rate/priority policy the driver actually uses.
- Avoid long IRQ-masked table lookup or voice preparation. Publish only the
  small state transition that must be atomic.
- Preserve MPR mappings when a timer/audio path reads banked data.
- Test effects alone, together with music, with raster work, at bank boundaries,
  and through stop/restart/loop transitions.
- A host audio preview does not prove target decoder compatibility or timing.

Use the example recipes for [visual asset loading](../examples/02-static-screen/README.md),
[CD extent loading](../examples/03-cd-to-aram-files/README.md),
[animation swaps](../examples/07-large-animation/README.md), and
[sound samples](../examples/05-sound-samples/README.md). The reusable PNG converters,
ADPCM encoders, and BIOS player wrapper are catalogued in
[`tools/pce/README.md`](../tools/pce/README.md); gameplay recipes based on the
Saber Rider PCE port are listed in [examples/README.md](../examples/README.md).
