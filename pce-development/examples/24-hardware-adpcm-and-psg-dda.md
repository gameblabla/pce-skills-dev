# Example 24: hardware ADPCM and timer-driven PSG DDA

**Build contract:** Copy the shared starter files. The host audio tools require ffmpeg. The software ADPCM encoder and two-voice player include their lookup tables, so no source ROM is needed. This public bundle contains no game ROM or extracted sound samples.

The PCE CD hardware ADPCM unit and PSG DDA output are different playback paths. Saber Rider uses the CD BIOS ADPCM unit for character voices and the PSG DDA channels for short samples and a looping gallop. CD-DA music is a third path. Keep their storage and ownership rules separate.

## CD hardware ADPCM voice

The common compressor converts an input file to mono PCM at the requested source rate, encodes high-nibble-first ADPCM, and writes a decoded WAV preview plus a JSON sidecar:

    python3 pce-development/tools/pce/compress_adpcm.py voice.wav build/voice.adpcm --rate TARGET_RATE

The raw stream does not contain a project-specific BIOS divider or CD sector table. Package it at a sector boundary, retain its exact byte length, and choose the playback divider for the source's actual rate. The LLVM-MOS PCE CD BIOS exposes reset, read-from-CD, play, stop, and status calls in pce/cd/bios.h. The shared [`adpcm_player.c`](../tools/pce/adpcm_player.c) wrapper reads a cue's sectors into ADPCM RAM and plays its exact byte length as a one-shot. Call it from the main loop, coordinate its blocking drive access with CD-DA, and check the returned BIOS error code. Its priority check refuses a lower-priority cue while a higher-priority voice is active.

The Saber Rider port permits one hardware ADPCM voice at a time. It applies priorities before stopping/restarting the voice, loads the selected hero's voice bank before playback, and avoids replacing code/data while music or a blocking loader owns the drive.

## SoftADPCM 2-bit codec feeding PSG DDA

TurboXRay created the original SoftADPCM codec and decoder. The bundled
converter and player use its adaptive decoder tables in
`tools/pce/softadpcm_tables.py` and `softadpcm_tables.c`; the source ROM is not
needed to encode audio, build the library, or run it:

    python3 pce-development/tools/pce/softadpcm.py effect.wav build/effect.softadpcm --rate 6991

This writes a packed 2-bit stream, a signed decoded WAV preview, metadata, and a `.dda` file of 5-bit PSG DAC values. The `.dda` values use the Saber Rider conversion from the decoder's signed output to the PSG's 0..31 sample range. Preserve the metadata's sample count; the raw streams have no embedded length.

The common [SoftADPCM player library](../tools/pce/README.md#softadpcm-runtime-player) preserves the earlier runtime-decoder option: its IRQ decodes each packed code using the bundled tables and writes 5-bit DDA values. It supports two independent voices. Keep its 33-byte state in reserved direct-page RAM, its decoder and tables in fixed mapped memory, and each sample inside one bank visible through MPR6. CD-ROM² projects can use the included BIOS IRQ adapter; HuCard projects attach the RTI handler to their timer vector.

Saber Rider later expanded the packed stream during asset generation, so the timer IRQ did not decode predictors or read adaptation tables. Its predecoded player still advanced banked pointers and counts, restored MPR6, and stopped the timer when both voices finished. The runtime decoder measured 31.24% of total CPU cycles for two voices (37.59% with its IRQ wrapper, excluding BIOS dispatch); predecoded DDA measured 17.30% for the sample service and 24.34% with the wrapper. Those are isolated project/emulator measurements, not console guarantees. The common player README records its memory and IRQ integration contract.

## Player ownership and timing

- The PSG channel select register is shared global state. Protect the short setup/write sequence from other PSG users; do not hold interrupts off for an entire sample or fade.
- Keep the DDA IRQ bounded and independent of HBlank road work. Predecode during the host build.
- Stop the timer and every owned PSG voice before a blocking disc load or before reusing their sample banks.
- For banked samples, test address wrap, count borrow, loop restart, and MPR restoration with samples placed at the end of a bank.
- Measure sound output or inspect emulator audio separately from checking that IRQ counters advanced. A successful code path is not proof of audible playback.

The case-study runtime is Saber Rider's src/platform/pce/audio_pcm.c and audio_pcm.S. Its sample preparation is tools/pce/build_audio.py and tools/pce/adpcm2.py. The public host tools retain the codec/compression behavior but omit Saber Rider's sample assets, ROM, custom linker banks, and overlay trampoline.
