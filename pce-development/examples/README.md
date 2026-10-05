# PC Engine / CD-ROM² example projects

Each numbered entry is a standalone project folder containing a Makefile, README, C source under `src/`, assets under `assets/`, and a local copy of the LLVM-MOS bootstrap tools. Run `make` to build a HuCard `.pce` ROM; each README embeds a Mednafen headless screenshot captured after 120 frames. A bootable CD-ROM² release still needs project-specific IPL/disc packaging and a user-supplied System Card BIOS; `make bios-check` reports the local BIOS setup path.

Every project includes a compact PCE screen fixture in `src/demo_video.c` and `assets/demo_assets.h`. The feature-specific entry point is `src/main.c`; use the folder README to follow the target design, constraints, and next adaptation steps.

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

## Shared converters and audio modules

The standalone host tools and target-side reference modules are documented in [`../tools/pce/README.md`](../tools/pce/README.md).

## Starting a project

The `00-project-template/` folder demonstrates the layout. The shared bootstrap is in `starter/`; each example has a local copy of the bootstrap files under `tools/`. See [`../references/toolchain-setup.md`](../references/toolchain-setup.md).
