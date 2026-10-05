# Example 09: racing and scanline road rendering

![Example 09: racing and scanline road rendering emulator screenshot](assets/screenshot.png)

**Project:** Run `make` in this folder to build `build/09-racing.pce` with the bundled LLVM-MOS setup. This HuCard ROM can run in a PC Engine emulator. CD-ROM² deployment needs project-specific IPL/disc packaging and a user-supplied System Card BIOS.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable source artwork. `assets/screenshot.png` is captured from the built ROM in the headless emulator. See additional files in this folder for topic-specific data.

A racing project may combine a road/camera model, car handling, opponent
simulation, a VDC background, sprites, and scanline scroll values. Keep the
simulation's road coordinates and camera transform shared by cars, pickups,
projectiles, and road geometry; a camera built from a different heading can
make distant rows swing or wrap unexpectedly.

## Raster data path

```text
offline_or_frame_update:
    generate_next_road_parameter_page()
    validate_every_scanline_entry()
    mark_page_pending()

vblank:
    publish_pending_page_if_complete()

hblank_for_each_visible_line:
    read_active_page_entry()
    write_vdc_scroll_registers_before_line_latch()
```

The routine names are descriptive, not SDK APIs. Confirm when the hardware
latches scroll registers, which interrupt entry/return convention the BIOS
expects, and which registers/MPR values the handler must preserve. Keep the
HBlank handler bounded and measure its worst-case latency while CD, sound,
sprite transfer, and game code are active. Use short transfer chunks derived
from that measured deadline; no burst length is universally safe.

## Test plan

Check a stationary car/road, steering in both directions, camera following,
wrap and horizon edges, simultaneous fire/effects, and maximum opponent load.
Capture scanline-table output and the image. If table bytes remain stable while
pixels shift, measure interrupt latency and publication timing before changing
the camera math. Use Python for angle/fixed-point/buffer calculations and the
emulator profiler for measured cycles.
