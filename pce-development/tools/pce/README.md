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
| `adpcm_build14.py` | Audio to the Saber Rider Build 14 2-bit stream, predecoded PSG DDA bytes, WAV preview, and manifest. Requires `--rom` pointing to a compatible user-supplied decoder ROM. |

The image converters require Python 3, NumPy, and Pillow. Audio conversion
requires ffmpeg. Run each script with `--help` for supported arguments. The
compressor outputs are deliberately raw; preserve their exact lengths and
manifest metadata when packaging them for a project.

`adpcm_build14.py` reads the decoder's adaptation tables from the supplied ROM
and records its hash. It does not download, redistribute, or embed that ROM.
Its `.dda` output is 5-bit PSG sample data decoded at build time, so the
runtime does not spend timer IRQ time on the Build 14 predictor.

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
Saber Rider's assembly player uses fixed RAM state, mapped sample banks, and
its own IRQ budget; adapt those details to the active project's linker and
bank lifetime instead of copying its private overlay wiring.
