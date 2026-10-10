# PC Engine / CD-ROM² example projects

Runnable examples 00–24, 26 and 27 are standalone project folders containing a Makefile,
README, and C source under `src/`, with graphics assets only where needed. Run
`make` to build a HuCard `.pce` ROM; graphics examples have headless screenshot
captures, while non-visual examples do not. Example 25 is
a cross-feature integration case study, not a standalone project. A bootable
CD-ROM² release still needs project-specific IPL/disc packaging and a
user-supplied System Card BIOS; `make bios-check` reports the local BIOS setup
path. The examples include `make run` for a bounded headless capture and
`make debug` for a capture plus execution coverage; CD examples require their
packaged disc image and System Card to be configured first.

Graphics-focused projects use the PCE screen fixture in `src/demo_video.c` and `assets/demo_assets.h`. Boot, CPU, I/O, CD, bank, diagnostic, and audio examples intentionally do not initialize or render graphics. Their results are observable through the debugger, hardware state, or sound. Every topic-specific entry point is in `src/main.c`.

**Small examples:** The [`micro/`](micro/README.md) collection adds 95 much smaller, single-topic HuCard projects. Each has one C file, a one-line Makefile, and minimal shared build helpers. The audio projects never use a graphics fixture. Run `cd micro && python3 check.py` to build all.

## Projects

- [Example 00: project template](00-project-template/README.md)
- [Example 01: CD-ROM² Hello World boot](01-cdrom2-hello/README.md)
- [Example 02: static screen and background](02-static-screen/README.md)
- [Example 03: CD sectors to Arcade RAM and named files](03-cd-to-aram-files/README.md)
- [Example 04: Arcade RAM to VRAM with block transfers](04-aram-to-vram/README.md)
- [Example 05: sound samples and music](05-sound-samples/README.md)
- [Example 06: sprites, SAT, and admission](06-sprites-and-sat/README.md)
- [Example 07: large animation by staged pattern swaps](07-large-animation/README.md)
- [Example 08: 2D platformer](08-platformer/README.md)
- [Example 09: racing and scanline road rendering](09-racing/README.md)
- [Example 10: scrolling shooter](10-shmup/README.md)
- [Example 11: “The HUD is too low; move it higher”](11-visual-request/README.md)
- [Example 12: relocate code when a bank is full](12-bank-relocation/README.md)
- [Example 13: headless emulator and MCP debugging](13-headless-debugging/README.md)
- [Example 14: calculate with Python](14-python-math/README.md)
- [Example 15: 320-dot and 512-dot display modes](15-video-modes-320-and-512/README.md)
- [Example 16: convert and display a static picture](16-static-picture-and-conversion/README.md)
- [Example 17: stream a scrollable background](17-scrollable-background/README.md)
- [Example 18: scrolling player with collision](18-scroll-player-and-collision/README.md)
- [Example 19: enemies, projectiles, and hit rules](19-enemies-and-shooting/README.md)
- [Example 20: efficient fades to and from black](20-palette-fades/README.md)
- [Example 21: draw text with a custom bitmap font](21-text-and-bitmap-fonts/README.md)
- [Example 22: parallax from raster scroll bands](22-raster-parallax/README.md)
- [Example 23: plan CPU, VRAM, Arcade RAM, and audio memory](23-memory-management/README.md)
- [Example 24: hardware ADPCM and timer-driven PSG DDA](24-hardware-adpcm-and-psg-dda/README.md)
- [Example 25: integrate platformer collision, scrolling, and HUD](25-platformer-integration/README.md)
- [Example 26: runnable platformer starter and real P2TR telemetry](26-platformer-starter/README.md)
- [Example 27: platformer/racing phase transition with explicit X/Y rules](27-platformer-racer/README.md)

## Shared converters and audio modules

The standalone host tools and target-side reference modules are documented in [`../tools/pce/README.md`](../tools/pce/README.md).

For offline local-model guidance and a reproducible starter, use [`../workflows/README.md`](../workflows/README.md).

## Starting a project

The `00-project-template/` folder demonstrates the layout. The shared bootstrap is in `starter/`; each example has a local copy of the bootstrap files under `tools/`. See [`../references/toolchain-setup.md`](../references/toolchain-setup.md).

## Rebuilding the graphics and screenshots

The graphics examples use original indexed artwork with a shared 16-color VCE palette.
Each ROM loads its generated background patterns and full BAT from
`assets/demo_assets.h`; `assets/source.png` shows the initial viewport before
runtime sprites, scroll, and palette changes. `assets/sprite-sheet.png` holds
the player, projectile, enemy, HUD icon, and two robot poses. The old repeating
four-tile screen fixture has been replaced with topic-specific art.

From the bundle root (`pce-skills-dev/`), with Pillow and NumPy installed:

```sh
python3 pce-development/examples/tools/generate_graphics.py
python3 pce-development/examples/tools/capture_screenshots.py
```

Both commands accept `--example NUMBER` to update one graphics project. Non-visual examples are skipped intentionally. The capture
command builds the ROM and runs 120 frames with all controller buttons
released, using the bundled headless emulator; build that emulator first or
pass `--emulator PATH`. Its captures are actual emulator output. The source art
is not substituted for a screenshot. See the [graphics tools guide](tools/README.md).

The numbered projects reserve a fixed ROM window beginning at 0x8000 for
embedded graphics. Background patterns start at VRAM word address 0x0800,
the custom font at 0x5000, sprite patterns at 0x6000, and the SAT at 0x7f00.
The bank-relocation worker uses physical bank 4 outside the fixed ROM window.
The CD, Arcade Card, and audio diagrams illustrate those topics; the default
HuCard demos retain the deployment limitations described in their READMEs.
