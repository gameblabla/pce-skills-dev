# Example 21: draw text with a custom bitmap font

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/21-text-and-bitmap-fonts.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

Run the shared converter on a bright-on-dark or bright-on-transparent PNG glyph sheet. Cells are read left-to-right, top-to-bottom:

    python3 pce-development/tools/pce/bitmap_font.py font.png --out build/font --first-code 32 --count 96 --pattern-word 0x4200 --palette 15 --ink 0x1ff

The tool emits four-plane background patterns, a palette set, a PNG preview of the thresholded glyph mask, a small C header, and a JSON manifest. By default foreground pixels use pen 15 and the font tile base matches Saber Rider's VDC word address 0x4200. Change those placements when another asset already owns that VRAM range.

## BAT text path

Saber Rider loads 96 printable glyph patterns and renders text by writing BAT entries. Character code 32 maps to the first font tile; unsupported bytes are replaced with question mark. Palette 15 is reserved for text, and its final color entry is forced to white after scene palettes load. The game has a separate doubled-cell path for the 512-dot race renderer; normal platform text stays in the scrolled playfield while HUD text is submitted before world sprites.

The core operation is:

    tile = font_tile_base + (character_code - first_code)
    bat_word = tile | (text_palette << 12)
    write_bat_word(row * bat_stride + column, bat_word)

This is descriptive pseudocode. Derive tile index from the VDC word address by dividing the pattern address by the VDC's 16-word character size; use the active SDK's actual VDC functions or the project's VDC write helper. Keep the output tile base and the runtime BAT entry consistent.

The Saber Rider runtime implementation is video_text() in src/platform/pce/video_pce.c. Its bitmap glyphs are baked by tools/pce/build_assets.py from font frames; the public bitmap_font.py tool replaces that asset-specific extraction with a normal PNG glyph sheet.

## Font checks

- Verify space and all printable glyph cells, especially punctuation and characters at both ends of the requested range.
- Check that the threshold preview matches the bitmap art and that transparent pixels encode as pen zero.
- Check the palette after all scene palette loads; preserve the foreground color used by the text pen.
- Place text on a scrolled screen and confirm column wrapping and row stride.
- Keep the font tile allocation outside the background cache, SAT patterns, and BAT memory.
