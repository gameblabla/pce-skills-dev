# Why the examples are separated

The original repository history shows two distinct steps:

- `2568d310` introduced examples and tools based on lessons from the PCE port
  of Saber Rider.
- `2e74e3ea` made recipes standalone projects.
- `8d0620f1` and `a24f154d` added emulator captures and increasingly
  elaborate graphics to those standalone projects.

Those captures helped graphical checks, but retaining the same tile, palette,
VBlank and rendering support in CPU-only, audio, CD, banking or tooling lessons
added unrelated dependencies and misleading visual feedback. This revision
removes that scaffold from non-visual examples and leaves visual captures with
graphics projects. The recipes remain available as references; the new
`examples/micro/` directory offers a separate single-function starting point.

## Reference material

- `gameblabla/SaberRiderStarSheriffUnOfficial`, branch `sv24_2`:
  `src/platform/pce/psg_pce.c` programs PSG channels and tone waveforms;
  `src/platform/pce/audio_pcm.c` and `audio_pcm.S` keep timer-driven DDA distinct
  from tone/noise and hardware CD ADPCM; `src/platform/pce/video_pce.c` shows
  VDC state discipline; `src/platform/pce/arcade_pce.c` shows Arcade Card port
  stride, address setup, and byte access.
- The bundled LLVM-MOS 23.2.0 PCE SDK headers are authoritative for these
  example API names and register definitions (`pce/hardware.h`, `pce/vdc.h`,
  `pce/system.h`).

No Saber Rider assets, scripts, game code or project-specific linker banks
are imported into the micro examples. They are instructional snippets, not a
replacement for the actual game-specific loaders or audio scheduler.

## Rules when adding an example

1. Exactly one topic per `main.c`. Put unrelated setup in an optional shared
   helper only when the helper is truly unavoidable.
2. Audio has no VDC/VCE, tile, font, sprite, HUD, or screenshot dependency.
   Inspect audio playback separately; a blank image is expected.
3. CPU/input/IRQs/CD/memory/banking may expose a `volatile` debugger symbol
   instead of pretending a change to the palette proves the subsystem works.
4. Video samples can use tiles and palette state but should not introduce
   PSG setup as a side effect.
5. Explicitly distinguish the HuCard preview (`mos-pce-clang`) from a
   Super CD-ROM2 disc image with an IPL and System Card BIOS. Hardware ADPCM
   needs the appropriate CD hardware; the advanced SoftADPCM cue is a
   packaging template, not a provisioned sample bank.
6. Do not disguise software delay loops as precise PCM timing, VBlank sync or
   audio-rate clock sources. Reserve those for a proper timer IRQ player.
7. Prefer compiled ROMs, debugger state and measured audio output over
   assertions that a C program "should" behave a certain way on hardware.

## Local verification

With the pinned LLVM-MOS SDK on PATH:

```sh
cd pce-development/examples/micro
python3 check.py
cd ../05-sound-samples
make
```

The project builds are compile/link checks; runtime tests must use `make run`
or `make debug`, with the configured headless frontend and sensible feature
checks. A render is evidence of drawing only; an emulator's black audio-ROM
screenshot is not proof of playback. A ROM running in an emulator is not a
verified physical-machine test.
