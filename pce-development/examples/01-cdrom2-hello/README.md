# Example 01: CD-ROM² Hello World boot

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/01-cdrom2-hello.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

## Goal

Reset through the System Card/BIOS, load the project's IPL and application
from the disc, initialize the video hardware, and display a stable message.

## Build the path

- IPL: starts in the memory/configuration provided by the chosen system card,
  requests the application extent, maps only the banks the linker assigned
  through the correct MPRs, and jumps through the defined application entry
  symbol.
- Image builder: records the IPL and application extents and reports sector
  locations; the IPL must not rely on a hand-entered sector that can drift.
- Application entry: checks the expected machine/card revision, initializes
  VCE palette and VDC mode, loads a small character set, fills BAT entries, and
  enables background display after its data is ready.
- Main loop: waits for the project's frame signal, polls one input, updates a
  heartbeat, and republishes the frame consistently.

Control-flow sketch (**pseudocode**, bind it to the LLVM-MOS PCE CD SDK's boot
and video API):

```text
ipl_entry:
    initialize_cd_interface()
    if system_card_version_is_unsupported(): show_boot_error_forever()
    extent = disc_manifest.lookup("application")
    if !read_extent_to_linked_app_banks(extent): show_disc_error_forever()
    map_application_banks_with_mprs()
    jump(application_entry)

application_entry:
    initialize_palette_and_vdc()
    upload(message_patterns)
    write_message_bat_cells()
    enable_display()
    loop:
        wait_vblank()
        poll_input()
        update_heartbeat()
```

The sketch deliberately omits register names, MPR values, sector sizes, and
BIOS calls: obtain those from the selected LLVM-MOS PCE CD SDK and linker, then confirm
the emitted IPL in disassembly. Do not copy addresses from a different card or
compiler build.

## Bring-up assertions

- Disc packaging contains the IPL and application extents expected by the
  linker symbols/manifest.
- The application entry executes after a cold reset with the intended BIOS.
- Unsupported BIOS and failed CD reads show a visible diagnostic.
- The screenshot contains the expected message and palette, not only a BIOS
  screen.
- Input or heartbeat changes after multiple frame boundaries.

Test cold boot and reset. If save states are used, state explicitly that they
do not replace a cold-boot check.
