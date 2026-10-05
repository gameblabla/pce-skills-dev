# Example 02: static screen and background

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/02-static-screen.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

## Offline asset stage

Convert the source image into the target VDC representation before runtime:

1. Select legal colors for each palette and quantize the source into the
   target's background palette format.
2. Split into character patterns and deduplicate identical patterns.
3. Generate BAT entries that select each pattern and palette.
4. Emit a manifest with source checksum, palette data, pattern count, BAT
   dimensions, and output byte counts.
5. Produce a host preview from the emitted data so the preview tests the actual
   runtime representation rather than the original image.

## Runtime stage

```text
hide_or_blank_display_if_required()
copy_palette_to_vce(manifest.palette)
copy_patterns_to_vram(manifest.patterns, assigned_pattern_region)
copy_bat_to_vram(manifest.bat, assigned_bat_region)
set_scroll_origin(0, 0)
publish_video_mode_and_enable_background()
```

The calls are descriptive placeholders. The target adapter must use its SDK's
actual VRAM address units and VDC data-port sequencing. Verify whether an
address is expressed in bytes, words, or pattern numbers at every boundary.

## Verify

- Capture the rebuilt image in the intended screen mode and compare with the
  generated preview.
- Check palette index zero/transparency and every palette bank used.
- Validate the first and last BAT/pattern entries from the manifest.
- Confirm the display becomes visible only after all referenced patterns are
  present.
- Keep a test that rejects out-of-range VRAM writes.

Use Python for palette/pattern counts and byte-range calculations. Do not
assume the nominal pattern-region size is available until the project's font,
SAT, clipping, and other allocations are included.
