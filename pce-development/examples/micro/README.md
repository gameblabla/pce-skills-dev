# Small, single-purpose PC Engine examples

25 separate LLVM-MOS HuCard C projects. Each contains **one `main.c` and one two-line Makefile**; the build rules and optional tiny helpers are shared at this level. Audio examples never touch the VDC, VCE, screen, graphics, fonts or sprites. No commercial ROM or BIOS is needed to build these.

Build one: `cd 03-psg-tone && make`. Run through the configured headless frontend via
`make run` or `make debug`; both forward to the standard project wrapper.
Or build/test all: `python3 check.py`.

**Scope:** HuCard by default; these are not bootable CD image files. Memory outputs are observable via emulator debugger rather than by rendering status text. Sound output needs audio capture/listening for runtime verification; compilation alone cannot prove audible playback.

## Index

- [00-cpu-loop](00-cpu-loop/README.md) — CPU: Minimal C entry point; no video, sound or peripheral initialization.
- [01-joypad-state](01-joypad-state/README.md) — Input: Read the active-low joypad and store pressed buttons. Nothing is drawn.
- [02-joypad-edges](02-joypad-edges/README.md) — Input: Detect fresh presses without adding an on-screen HUD.
- [03-psg-tone](03-psg-tone/README.md) — Audio: Continuous PSG tone on channel 0; no VDC, VCE, fonts or graphics.
- [04-psg-sweep](04-psg-sweep/README.md) — Audio: Sweep one PSG tone. CPU delays are approximate, not accurate note timing.
- [05-psg-stereo](05-psg-stereo/README.md) — Audio: Alternate sound balance left/right on a single PSG tone.
- [06-psg-volume](06-psg-volume/README.md) — Audio: Fade a PSG tone with the 5-bit channel amplitude control.
- [07-psg-two-tones](07-psg-two-tones/README.md) — Audio: Two PSG channels with distinct frequencies, using the same tiny wave shape.
- [08-psg-noise](08-psg-noise/README.md) — Audio: PSG white-noise effect on hardware noise channel 4.
- [09-psg-dda](09-psg-dda/README.md) — Audio: Direct PSG DAC writes at CPU speed; no 60 Hz screen updates. This is a pitch/timing demonstration, not stable sampled-audio playback.
- [10-psg-stop](10-psg-stop/README.md) — Audio: Start a tone, then explicitly stop it, without turning on display hardware.
- [11-vce-backdrop](11-vce-backdrop/README.md) — Graphics: Set VCE color zero with display timing but no BAT, sprites or font.
- [12-vce-colors](12-vce-colors/README.md) — Graphics: Demonstrate two VCE palette colors with an 8x8 tiled backdrop.
- [13-vdc-scroll-x](13-vdc-scroll-x/README.md) — Graphics: Scroll a simple tiled background horizontally.
- [14-vdc-scroll-y](14-vdc-scroll-y/README.md) — Graphics: Scroll a simple tiled background vertically.
- [15-vce-palette-cycle](15-vce-palette-cycle/README.md) — Graphics: Cycle one visible background-tile color.
- [16-vdc-vram-readback](16-vdc-vram-readback/README.md) — Graphics: Write a small tile then read it back; check bytes using a debugger.
- [17-supergrafx-detect](17-supergrafx-detect/README.md) — SuperGrafx: Check for extra VDC hardware; no video output or compositing is attempted.
- [18-supergrafx-vdc2](18-supergrafx-vdc2/README.md) — SuperGrafx: Initialize and address SuperGrafx VDC2, then switch back; no compositing claim.
- [19-arcade-card-detect](19-arcade-card-detect/README.md) — Arcade Card: Read Arcade Card identification byte; works without graphics or disc.
- [20-arcade-card-port](20-arcade-card-port/README.md) — Arcade Card: Write/read eight bytes via Arcade Card port zero with proper 16-bit offset setup. Requires Arcade Card.
- [21-timer-irq](21-timer-irq/README.md) — CPU/IRQ: Tick a volatile counter from the CPU timer IRQ; no video wait.
- [22-vdc-vblank-irq](22-vdc-vblank-irq/README.md) — Graphics: Count VDC VBlank interrupts for frame timing; no text.
- [23-psg-melody](23-psg-melody/README.md) — Audio: Play three notes on PSG channel zero, changing only the pitch register.
- [24-psg-noise-sweep](24-psg-noise-sweep/README.md) — Audio: Change noise divider on PSG channel 5 without relying on visuals.

## Code origin and constraints

Hardware API/register names are from the pinned LLVM-MOS SDK; the project layout was inspired by the existing recipes. The PSG channel ownership and DDA separation follow the `sv24_2` branch of gameblabla/SaberRiderStarSheriffUnOfficial (`src/platform/pce/psg_pce.c`, `audio_pcm.c`, `video_pce.c`). There is no Saber Rider game code or asset copied into these small projects.

Do not combine these snippets verbatim without sharing PSG channel ownership, IRQ vectors, VDC-index state, and memory maps. Busy-wait loops are instructional only. SuperGrafx VDC2 selection does not activate automatic dual-plane compositing. Arcade Card examples require its optional hardware.
