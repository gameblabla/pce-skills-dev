# Small, single-purpose PC Engine examples

99 separate LLVM-MOS HuCard C projects. Each contains **one `main.c` and one one-line Makefile**; the build rules and optional tiny helpers are shared at this level. Audio examples never touch the VDC, VCE, screen, graphics, fonts or sprites. New sprite examples use a graphics-only helper, independent of the PSG. No commercial ROM or BIOS is needed to build these.

Build one: `cd 03-psg-tone && make`. Run through the configured headless frontend via
`make run` or `make debug`; both forward to the standard project wrapper.
Or build/test all: `python3 check.py`. Use `python3 check.py --lint-only` for static separation checks without the toolchain. Run `python3 check.py --self-test` to confirm the separation rules reject intentionally mixed examples. With Pillow and the configured headless frontend, `python3 check.py --smoke` also checks the audio ROM draws nothing and the sprite ROM draws a visible sprite.

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

- [25-joypad-release](25-joypad-release/README.md) — Input: Detect buttons released since the previous poll.
- [26-joypad-multitap](26-joypad-multitap/README.md) — Input: Read a second controller when a multitap is connected. No display.
- [27-joypad-press-counter](27-joypad-press-counter/README.md) — Input: Count new presses of button I; inspect the value in a debugger.
- [28-psg-triangle-wave](28-psg-triangle-wave/README.md) — Audio: Write a rising/falling 32-sample PSG waveform, then play it.
- [29-psg-saw-wave](29-psg-saw-wave/README.md) — Audio: Load a rising 32-sample sawtooth; no screen output.
- [30-psg-channel-selection](30-psg-channel-selection/README.md) — Audio: Demonstrate that channel selection affects subsequent PSG register writes.
- [31-psg-master-balance](31-psg-master-balance/README.md) — Audio: Alternate left/right master PSG balance without touching video.
- [32-psg-note-table](32-psg-note-table/README.md) — Audio: Read a small note table and write only the PSG period register.
- [33-psg-tone-and-noise](33-psg-tone-and-noise/README.md) — Audio: Use channel 0 for tone and channel 5 for noise simultaneously.
- [34-psg-channel-mute](34-psg-channel-mute/README.md) — Audio: Silence only the chosen PSG channel after a brief busy wait.
- [35-psg-noise-burst](35-psg-noise-burst/README.md) — Audio: Play a short noise burst on PSG channel 4, then stop it.
- [36-psg-dda-ramp](36-psg-dda-ramp/README.md) — Audio: Write a repeating 5-bit ramp in PSG DDA mode; rate is CPU-dependent.
- [37-vce-color-readback](37-vce-color-readback/README.md) — Graphics: Write one VCE palette entry and read it back without text.
- [38-vce-palette-upload](38-vce-palette-upload/README.md) — Graphics: Upload a complete 16-color VCE background palette.
- [39-vdc-vram-copy](39-vdc-vram-copy/README.md) — Graphics: Upload exactly one 8x8, 4bpp tile (32 bytes) to VDC VRAM.
- [40-vdc-vram-clear](40-vdc-vram-clear/README.md) — Graphics: Clear a small VRAM region using a zero-filled CPU buffer.
- [41-vdc-register-readback](41-vdc-register-readback/README.md) — Graphics: Read the VDC background scroll register into a debugger-visible variable.
- [42-vdc-bat-write](42-vdc-bat-write/README.md) — Graphics: Write one BAT entry that points to character pattern at VRAM word 0x0800.
- [43-vdc-reset-scroll](43-vdc-reset-scroll/README.md) — Graphics: Reset both VDC background scroll registers to zero.
- [44-vdc-bg-toggle](44-vdc-bg-toggle/README.md) — Graphics: Toggle the VDC background layer without touching audio hardware.
- [45-vdc-dma-copy](45-vdc-dma-copy/README.md) — Graphics: Copy a tile between two VDC VRAM addresses using VRAM-to-VRAM DMA.
- [46-supergrafx-vdc2-vram](46-supergrafx-vdc2-vram/README.md) — SuperGrafx: Access VDC2 VRAM independently, only after detecting SuperGrafx hardware.
- [47-arcade-card-port-one](47-arcade-card-port-one/README.md) — Arcade Card: Exercise data port 1 (0x1a10) with its own 16-bit address register.
- [48-arcade-card-boundary](48-arcade-card-boundary/README.md) — Arcade Card: Test Arcade Card automatic address carry across the 64 KiB boundary.
- [49-timer-irq-stop](49-timer-irq-stop/README.md) — CPU/IRQ: Stop the timer after 100 IRQ callbacks; no VBlank or video dependency.
- [50-cpu-block-copy](50-cpu-block-copy/README.md) — CPU: Use the HuC6280 block transfer helper to copy RAM; inspect success in debugger.
- [51-cpu-block-pattern](51-cpu-block-pattern/README.md) — CPU: Use the alternating-source HuC6280 transfer mode to repeat two RAM bytes.
- [52-cpu-bank-map](52-cpu-bank-map/README.md) — CPU: Read the currently mapped MPR3 bank without remapping executable code.
- [53-cpu-irq-mask](53-cpu-irq-mask/README.md) — CPU/IRQ: Show explicit CPU IRQ masking around one byte update.
- [54-vce-color-zero-toggle](54-vce-color-zero-toggle/README.md) — Graphics: Switch only VCE backdrop color; no fonts, BAT or sprites.


- [55-joypad-run-edge](55-joypad-run-edge/README.md) — Input: Detect a new RUN press without drawing button state.
- [56-joypad-two-button-chord](56-joypad-two-button-chord/README.md) — Input: Detect buttons I and II held at the same time.
- [57-joypad-held-frames](57-joypad-held-frames/README.md) — Input: Count consecutive controller polls while LEFT is held (not real frames).
- [58-joypad-direction-mask](58-joypad-direction-mask/README.md) — Input: Keep only the four D-pad direction bits in a debugger-visible byte.
- [59-cpu-block-reverse](59-cpu-block-reverse/README.md) — CPU: Copy bytes backward with the HuC6280 TDD block-transfer mode.
- [60-cpu-block-fixed-dest](60-cpu-block-fixed-dest/README.md) — CPU: Use TIN to repeatedly overwrite one RAM byte; its final value is the last source byte.
- [61-cpu-block-alternate-dest](61-cpu-block-alternate-dest/README.md) — CPU: Use TIA to alternate writes to a pair of RAM bytes.
- [62-cpu-mpr-snapshot](62-cpu-mpr-snapshot/README.md) — CPU: Read MPR2, MPR3 and MPR4 mappings without altering bank registers.
- [63-psg-quarter-pulse](63-psg-quarter-pulse/README.md) — Audio: Load an eight-sample-high pulse wave into one 32-sample PSG channel.
- [64-psg-three-quarter-pulse](64-psg-three-quarter-pulse/README.md) — Audio: Load a 75% duty-cycle PSG pulse wave to contrast with the quarter pulse.
- [65-psg-volume-staircase](65-psg-volume-staircase/README.md) — Audio: Step one PSG channel through eight amplitude levels, no screen or VBlank.
- [66-psg-pitch-bend](66-psg-pitch-bend/README.md) — Audio: Bend one pitch gradually by changing only the PSG period.
- [67-psg-two-channel-interval](67-psg-two-channel-interval/README.md) — Audio: Start a second PSG channel at a different period using the same square waveform.
- [68-psg-three-channel-chord](68-psg-three-channel-chord/README.md) — Audio: Play a three-note PSG chord on channels 0, 1 and 2 without any graphics.
- [69-psg-melody-loop](69-psg-melody-loop/README.md) — Audio: Loop a four-period melody on PSG channel 0 with approximate CPU delays.
- [70-psg-noise-gate](70-psg-noise-gate/README.md) — Audio: Gate noise on and off using channel 5 noise enable, leaving display untouched.
- [71-psg-reload-wave](71-psg-reload-wave/README.md) — Audio: Turn off PSG channel 0, reload 32 waveform samples, then restart playback.
- [72-psg-master-mute](72-psg-master-mute/README.md) — Audio: Silence all PSG channels by setting global left/right volume to zero.
- [73-psg-dual-channel-pan](73-psg-dual-channel-pan/README.md) — Audio: Pan two PSG channels to opposite speakers using per-channel balance.
- [74-vdc-bat-row](74-vdc-bat-row/README.md) — Graphics: Alternate empty and patterned BAT entries in the first background row.
- [75-vdc-bat-column](75-vdc-bat-column/README.md) — Graphics: Blank one BAT column using 32-word VRAM increment mode.
- [76-vdc-bat-blank-stripe](76-vdc-bat-blank-stripe/README.md) — Graphics: Overwrite one visible BAT row with zero pattern entries to create a stripe.
- [77-vdc-scroll-diagonal](77-vdc-scroll-diagonal/README.md) — Graphics: Change horizontal and vertical background scroll together.
- [78-vdc-one-sprite](78-vdc-one-sprite/README.md) — Graphics: Show one hardware sprite with a solid generated pattern; no text or audio.
- [79-vdc-move-sprite](79-vdc-move-sprite/README.md) — Graphics: Move one sprite horizontally by rewriting a single SAT entry.
- [80-vdc-flip-sprite](80-vdc-flip-sprite/README.md) — Graphics: Toggle the sprite horizontal flip attribute in its SAT entry.
- [81-vdc-hide-sprite](81-vdc-hide-sprite/README.md) — Graphics: Hide and show a hardware sprite by changing just its Y coordinate.
- [82-vdc-sprite-palette](82-vdc-sprite-palette/README.md) — Graphics: Change a single sprite palette color, without changing the background palette.
- [83-arcade-card-port-two](83-arcade-card-port-two/README.md) — Arcade Card: Access Arcade Card RAM through data port 2 at 0x1a20.
- [84-arcade-card-independent-ports](84-arcade-card-independent-ports/README.md) — Arcade Card: Verify port 0 and port 1 have independent address counters.

- [85-bitmap-128-circle](85-bitmap-128-circle/README.md) — Graphics: Actual 512×224 BAT-backed pseudo-bitmap, 128×128 logical 4-bit pixels in VRAM; red filled circle built from constant pair-character patterns.
- [86-mode7-bitmap-floor](86-mode7-bitmap-floor/README.md) — Graphics: 512×224 high-resolution paired-BAT pseudo-bitmap with a 128×128 software perspective floor; 256 fixed pair tiles, 16 colours, raster-remapped BAT, not planar frame uploads.

Both bitmap lessons now use the 512×224 PCEdev paired-BAT scheme via [`bat_bitmap.h`](bat_bitmap.h), not ordinary per-frame planar tiles. The bitmap lessons have a [separate historical note](BITMAP_MODE7_HISTORY.md) tracing Saber Rider's old 19-strip Arcade Card floor, the replacement commit, and the deliberate teaching simplifications.

## Code origin and constraints

Hardware API/register names are from the pinned LLVM-MOS SDK; the project layout was inspired by the existing recipes. The PSG channel ownership and DDA separation follow the `sv24_2` branch of gameblabla/SaberRiderStarSheriffUnOfficial (`src/platform/pce/psg_pce.c`, `audio_pcm.c`, `video_pce.c`). There is no Saber Rider game code or asset copied into these small projects.

Sprite patterns use a 16x16 four-bitplane format; the SAT pattern field is in 32-word VRAM units (0x6000 words becomes 0x0300), and SATB DMA is enabled for publication on VBlank. The sprite example is deliberately asymmetric so flipping is visually detectable. The screenshot smoke check does not verify audio output.

Do not combine these snippets verbatim without sharing PSG channel ownership, IRQ vectors, VDC-index state, and memory maps. Busy-wait loops are instructional only. SuperGrafx VDC2 selection does not activate automatic dual-plane compositing. Arcade Card examples require its optional hardware.

## Gameplay building blocks (added)

- [87-cpu-q8-motion](87-cpu-q8-motion/README.md) — CPU: Track fractional Q8 horizontal movement without camera or graphics.
- [88-cpu-rect-overlap](88-cpu-rect-overlap/README.md) — CPU: Test axis-aligned hitboxes without any sprite or text code.
- [89-cpu-landing-crossing](89-cpu-landing-crossing/README.md) — CPU: Detect downward platform-top crossings using previous/current feet.
- [90-cpu-camera-follow](90-cpu-camera-follow/README.md) — CPU: Compute clamped world-to-screen camera offset; never move world positions.
- [91-cpu-lane-clamp](91-cpu-lane-clamp/README.md) — CPU: Clamp racing lane X independently of forward Y progress.
- [92-cpu-segment-state](92-cpu-segment-state/README.md) — CPU: Switch between platformer and racing rules with an explicit state machine.
- [93-joypad-jump-edge](93-joypad-jump-edge/README.md) — Input: Treat jump as a new press, not a repeated held-key action.
- [94-joypad-lane-steer](94-joypad-lane-steer/README.md) — Input: Use held LEFT/RIGHT to steer an independent lane X value without a display.

## Narrow arithmetic micro lessons

- [95-cpu-mul8](95-cpu-mul8/README.md) — CPU: Exact 8x8 multiply via libcommon, debugger-visible result; no renderer.
- [96-cpu-div16by8](96-cpu-div16by8/README.md) — CPU: Unsigned 16/8 division without compiler software divide. Not a speed benchmark.
- [97-cpu-signed-mul](97-cpu-signed-mul/README.md) — CPU: Signed 8x8 arithmetic including negative factors, without a runtime multiply.
- [98-cpu-mode7-lookup](98-cpu-mode7-lookup/README.md) — CPU: Mode7 depth/angle projection generated offline, no 32-bit math or target divide.

## Fast math link verification

`make arith-build` at the repository root checks examples 85 and 86 plus
95–98 for compiled math helpers, **not just source tokens**. Offline-generated
lookup tables are shared in `pce-development/libcommon`. Legacy CPU demos 87,
90 and 91 now use bounded 16-bit Q8/Q4 coordinates instead of 32-bit values.
