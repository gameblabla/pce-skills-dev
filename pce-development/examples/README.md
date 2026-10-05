# PC Engine / CD-ROM² project examples

This folder is a self-contained recipe library for a fresh project. It assumes
no game repository, exported conversation log, private BIOS, preinstalled
compiler, or compiled emulator binary is bundled. Project recipes use the
shared [starter Makefile](starter/Makefile): it accepts an existing
`mos-pce-clang` on `PATH`, or downloads and installs the pinned LLVM-MOS SDK
23.2.0 into user-local folders when that compiler is absent. See the
[toolchain and BIOS setup guide](../references/toolchain-setup.md). The adjacent
`third_party/mednafenPceDev-main/` directory contains the emulator source, build
notes, and MCP server source. If a user provides a base-code checkout, inspect
and adapt it; otherwise implement the small platform adapter against the
project's LLVM-MOS PCE CD SDK and linker.

Every recipe that creates or changes project code must copy the starter
Makefile and all files under `starter/tools/` into the new project. Include
`tools/llvm-mos-sdk.mk` in its Makefile, make every compile/assemble/link target
depend on `toolchain`, and make CD boot/test targets depend on `bios-check`.
The toolchain setup guide documents the interactive-shell `PATH` command and
the BIOS folder printed by `make bios-check` when firmware is missing.

Code blocks marked **Pseudocode** express control flow and data ownership; API
names are descriptive placeholders, not promised SDK symbols. Do not turn
them into C calls until the target headers/source confirm the matching API.

## Recipes

- [`00-project-template.md`](00-project-template.md): clean project layout,
  adapter boundary, build and test gates.
- [`01-cdrom2-hello.md`](01-cdrom2-hello.md): IPL/CD boot to a visible Hello
  World screen.
- [`02-static-screen.md`](02-static-screen.md): bake and display a static
  background with palettes, patterns, and BAT data.
- [`03-cd-to-aram-files.md`](03-cd-to-aram-files.md): read CD sectors, stage
  through CPU memory, and load named files into Arcade RAM.
- [`04-aram-to-vram.md`](04-aram-to-vram.md): verify Arcade RAM data and upload
  patterns to VDC VRAM with TAI/TIA CPU block-transfer instructions assembled
  by LLVM-MOS.
- [`05-sound-samples.md`](05-sound-samples.md): plan CD-DA, ADPCM, PSG DDA,
  and PSG effects around shared resources.
- [`06-sprites-and-sat.md`](06-sprites-and-sat.md): create sprites and admit
  them under SAT/scanline limits.
- [`07-large-animation.md`](07-large-animation.md): animate many frames by
  staging and swapping pattern data safely.
- [`08-platformer.md`](08-platformer.md): build a 2D platformer around
  collision maps, camera, actors, and streamed tiles.
- [`09-racing.md`](09-racing.md): combine road rendering, raster interrupts,
  vehicles, opponents, and HUD.
- [`10-shmup.md`](10-shmup.md): structure a shooter with deterministic waves,
  object pools, collision, and boss phases.
- [`11-visual-request.md`](11-visual-request.md): use an image plus source code
  to resolve “the HUD is too low; move it higher.”
- [`12-bank-relocation.md`](12-bank-relocation.md): handle a full code bank
  without breaking mapped calls or runtime data.
- [`13-headless-debugging.md`](13-headless-debugging.md): run and debug through
  a local headless emulator or MCP server.
- [`14-python-math.md`](14-python-math.md): use the included Python helpers
  for every calculation.
- [`15-video-modes-320-and-512.md`](15-video-modes-320-and-512.md): configure
  Saber Rider's 320-dot UI and 512-dot race modes.
- [`16-static-picture-and-conversion.md`](16-static-picture-and-conversion.md):
  convert and upload a static background.
- [`17-scrollable-background.md`](17-scrollable-background.md): stream a
  column-based scrolling map through a VBlank-safe cache.
- [`18-scroll-player-and-collision.md`](18-scroll-player-and-collision.md):
  combine world coordinates, camera scroll, and streamed collision data.
- [`19-enemies-and-shooting.md`](19-enemies-and-shooting.md): structure actor
  pools, projectiles, hit rules, and sprite admission.
- [`20-palette-fades.md`](20-palette-fades.md): fade old and new palettes
  efficiently through black.
- [`21-text-and-bitmap-fonts.md`](21-text-and-bitmap-fonts.md): draw BAT text
  from a converted bitmap font.
- [`22-raster-parallax.md`](22-raster-parallax.md): create layered motion with
  raster scroll bands.
- [`23-memory-management.md`](23-memory-management.md): plan CPU, VRAM, Arcade
  RAM, and audio memory lifetimes.
- [`24-hardware-adpcm-and-psg-dda.md`](24-hardware-adpcm-and-psg-dda.md):
  prepare and play BIOS ADPCM and timer-driven PSG DDA audio.

## Shared converters and audio modules

See [`../tools/pce/README.md`](../tools/pce/README.md) for the standalone PNG
converters, ADPCM compressors, BIOS ADPCM player wrapper, dependencies, and
asset output formats.

## Porting an existing base

The recipes describe an architecture; they do not replace the base port's
driver, linker, BIOS ABI, or compiler conventions. When base code is available,
map each adapter operation to a real function/section/register path and keep
the project's code. When it is absent, make that missing dependency explicit
and use the recipes only as the design contract. Never claim an example builds
until it has been adapted and compiled with the selected SDK.
