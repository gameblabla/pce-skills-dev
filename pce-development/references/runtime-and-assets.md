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

## Scrolling actors, collision, and HUD

Treat a platformer as one renderer/physics system, not a collection of separate
samples. Define a world-coordinate convention, actor collision box, sprite
anchor, camera position, map origin, and HUD space before implementing motion.
The visible sprite must be placed from the same actor state used by collision;
include hardware sprite-coordinate offsets in one named adapter and never add
the offset in both game code and the adapter.

- Define a platform by its collision rectangle and draw it from that same
  record. On a downward crossing, resolve the actor bottom to the platform top
  and clear vertical velocity; do not stop at whichever sample point first
  touched a broad solid region.
- Give each emitted SAT entry a unique slot. In the demo helper,
  `demo_draw_sprite()` always writes slot zero, so it cannot draw a row of
  platform pieces or a multi-sprite pole in a loop. Reserve documented slot
  ranges for world actors, effects, and HUD, hide unused entries each frame,
  and check the PCE's sprite-per-line and SAT limits.
- Keep world, camera, and screen coordinates separate. A sprite's screen
  coordinate is derived from world position and camera once. If the VDC
  background scrolls, also stream the correct world-map columns into its
  circular BAT; the small static demo BAT is not a long-level map and will
  repeat as the camera advances. Do not move world coordinates to fake camera
  motion.
- Inspect the actual starter BAT and source art. Demo backgrounds can contain
  instructional labels and sample geometry. Replace those assets for gameplay
  instead of carrying tutorial text into a moving playfield.
- A single scrolling background plane does not provide a stationary HUD by
  default. Put HUD glyphs in reserved screen-space sprite entries or implement
  and verify a deliberate raster-split/update strategy. A HUD must display
  actual timer/state values, remain legible during camera motion, and have an
  explicit priority policy relative to actors and background.
- Treat title, first gameplay frame, a landing, a mid-scroll scene, the level
  end, and transitions as separate visual states. A screenshot from a neutral
  input run proves only the state it captured. Use a project input harness or
  seeded state to reach movement and collision cases.
- Build incrementally with the active target's warning policy. Read SDK input
  masks and sprite flags from its headers, declare functions before use, and
  check generated initializer lengths against array dimensions. Choose an
  explicit fixed-point scale for fractional motion; assigning `0.5` to an
  integer velocity makes the actor stop. Rebuild after the last source edit so
  an old output image cannot be mistaken for the current program.

Use the [platformer integration example](../examples/25-platformer-integration/README.md)
as the acceptance list when combining examples 08, 17, 18, and 21.

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
