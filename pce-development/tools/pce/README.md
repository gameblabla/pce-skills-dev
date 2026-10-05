# Shared PC Engine asset and audio tools

These tools are adapted from Saber Rider's PCE host pipeline and generalized
for standalone projects. They contain no game assets, ROMs, BIOS files, or
game-specific archive layout. They produce host-side data; a project's loader,
VRAM allocation, and disc layout remain project-owned.

## Host tools

| Tool | Input and output |
| --- | --- |
| `picture.py` | PNG to deduplicated 8x8 background patterns, VCE palettes, padded BAT rows, preview, and JSON manifest. |
| `sprite_sheet.py` | PNG sprite or fixed-cell sheet to shared-palette 16x16 sprite patterns, per-frame SAT piece records, preview, and manifest. |
| `bitmap_font.py` | Row-major 8x8 glyph sheet to background font patterns, palette, preview, C header, and manifest. |
| `compress_adpcm.py` | Audio readable by ffmpeg to high-nibble-first CD ADPCM bytes, decoded WAV preview, and manifest. |
| `softadpcm.py` | Audio to the Build 14-compatible 2-bit SoftADPCM stream, predecoded PSG DDA bytes, WAV preview, and manifest. Uses the bundled decoder tables and needs no source ROM. |

The image converters require Python 3, NumPy, and Pillow. Audio conversion
requires ffmpeg. Run each script with `--help` for supported arguments. The
compressor outputs are deliberately raw; preserve their exact lengths and
manifest metadata when packaging them for a project.

`softadpcm.py` uses bundled adaptation tables in `softadpcm_tables.py` and
`softadpcm_tables.c`; no source ROM is needed to encode samples or build the
runtime library. Its `.dda` output is 5-bit PSG sample data decoded at build
time, so the runtime does not spend timer IRQ time on the SoftADPCM predictor.

## SoftADPCM runtime player

`softadpcm_player.S`, `softadpcm_player.c`, and `softadpcm_player.h` provide a
two-voice timer IRQ decoder for the SoftADPCM/HuCard-style software codec. It
reads low-pair-first 2-bit codes, uses the bundled lookup tables, and writes
decoded 5-bit values to PSG DDA. It does not call the CD BIOS and works on
HuCard or CD-ROM² hardware with the matching timer IRQ hookup. The separate
`adpcm_player.c` wrapper uses the CD hardware ADPCM unit and CD BIOS.

Encode a packed sample with the bundled tables:

    python3 pce-development/tools/pce/softadpcm.py effect.wav build/effect.softadpcm --rate 6991

Compile the bundled `softadpcm_tables.c` with the library. Its six arrays live
in the `.pce_softadpcm.tables` section. The IRQ decoder lives in
`.pce_softadpcm.text`; put both sections in a fixed CPU-visible region that
remains mapped while the IRQ can run. Keep each packed sample wholly inside one
physical bank mapped at CPU `$c000-$dfff` through MPR6.
`PceSoftAdpcmCue.sample_count` is the exact decoded sample count from the
compressor manifest, not the packed byte length.

The decoder state occupies 33 bytes of HuC6280 direct-page RAM. The default
base is `$2080`, matching Saber Rider's reserved range; override
`PCE_SOFTADPCM_STATE_ADDRESS` when assembling if that range is already used,
and reserve the resulting state and active byte from compiler allocations. The
timer is exclusively owned while either voice plays. Pass the desired timer
reload to `pce_softadpcm_init()`; for Saber Rider's nominal rate, use
`PCE_FREQ_TO_TIMER(6991)` from `pce/system.h`.

For CD-ROM², compile `softadpcm_player_cdrom2.c` and call
`pce_softadpcm_install_cdrom2_irq()`. For HuCard, install `pce_softadpcm_irq`
as the raw timer RTI handler, or call `pce_softadpcm_service()` from an
existing handler that clears decimal mode, preserves A/X/Y, acknowledges the
timer, and performs RTI itself. Start and stop cues with `pce_softadpcm_play()` and
`pce_softadpcm_stop()`; the cue selects decoder slot 0 or 1, PSG channel,
source bank/address, exact sample count, and loop mode. The player refuses two
simultaneous voices on the same PSG channel.

The historical Saber Rider emulator profile measured this runtime decoder at
31.24% of total CPU cycles for two voices (37.59% including its IRQ wrapper,
excluding BIOS dispatch). Its later predecoded 5-bit DDA path measured 17.30%
for the sample service and 24.34% including that wrapper. These are isolated
measurements from that project and emulator, not a hardware-wide guarantee.

## Target-side reference modules

`adpcm_player.c` and `.h` wrap the LLVM-MOS PCE CD BIOS for one prioritized,
one-shot hardware ADPCM voice. Each cue names its source sector range, ADPCM
buffer destination, exact byte length, BIOS divider, and priority. Call it from
the main loop: the BIOS CD read may block, and CD ownership must be coordinated
with CD-DA and other drive users. Confirm the cue's destination range fits the
active console's ADPCM buffer and that the packaged sector range covers the
sample before playback.

The timer-driven two-channel PSG DDA implementation is documented in
[`examples/24-hardware-adpcm-and-psg-dda.md`](../../examples/24-hardware-adpcm-and-psg-dda.md).
The included decoder adapts Saber Rider's measured runtime path; its state,
code/table placement, and sample-bank constraints are listed above.
