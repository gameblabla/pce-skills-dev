# Example 20: efficient fades to and from black

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/20-palette-fades.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

The Saber Rider transition snapshots all 32 palettes once, then computes each fade step from that unchanged snapshot. It does not repeatedly darken the previous step, so rounding errors do not accumulate. For each 9-bit VCE color it subtracts the fade level independently from the three 3-bit channels, clamping each channel at zero, then writes the full palette set at VBlank.

Fade out takes a snapshot and writes levels 1 through 7, waiting three video frames between levels. Fade in assumes the new screen has already been prepared: it snapshots that screen's palettes, writes black, turns display output on, and walks levels 6 down to 0 with the same cadence. The black transition is intentionally separate from setup so the next scene can load its palettes and patterns while the display remains dark.

## Transition sequence

    fade_out_old_screen_to_black()
    disable_display_for_asset_and_mode_change()
    load_new_screen_and_its_palettes()
    snapshot_new_palettes_and_write_black()
    publish_sat_and_scroll_for_new_screen()
    enable_display()
    fade_new_screen_up_from_black()

Use one palette snapshot buffer with explicit ownership. In Saber Rider, the shared staging buffer is also used by the renderer and asset loader; no other subsystem may overwrite the snapshot while a fade is in progress. Long palette writes should not mask raster interrupts for an unbounded time. The helper waits for the safe palette window instead.

Do not fade by modifying palette entries in place at every step unless losing the original values is acceptable. Avoid palette transitions while a raster effect is changing palette ownership. If the game queues one-palette writes for VBlank, check whether a 32-palette fade call is queued or synchronous before relying on it.

The Saber Rider version is in ui_fade(), ui_fade_out_body(), ui_black_body(), and ui_fade_in_body() in src/platform/pce/ui_pce.c. Its shared calls and snapshot-buffer ownership are documented in ui_pce.h and pce_config.h.

`src/main.c` is the compact version: it keeps one original 16-color palette,
computes each channel from that snapshot, and fades to and from black. Extend
the same calculation to the palettes owned by a full scene.
