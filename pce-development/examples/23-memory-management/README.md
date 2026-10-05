# Example 23: plan CPU, VRAM, Arcade RAM, and audio memory

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/23-memory-management.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

Treat each memory system as a separate allocator with a lifetime:

| Memory | Typical use | Allocation question |
| --- | --- | --- |
| CPU work RAM | stack, globals, collision cache, frame state, interrupt state | Which banks are always mapped while a callback or IRQ runs? |
| VDC VRAM | BAT, background characters, font, sprite patterns, SAT | Which regions can coexist in this display mode, and when may a slot be reused? |
| Arcade Card RAM | stage archives, map columns, source art, sample banks, code overlays | Which assets are resident, which are streamed, and which reads are legal during music/playback? |
| CD ADPCM RAM | hardware ADPCM one-shot voice data | Which single playback owns the device, and when may it be overwritten? |
| CD-DA | music tracks | Does a BIOS read or seek stall the game or conflict with voice loading? |

## Saber Rider bank layout as a case study

The current port keeps its resident kernel and IRQs in bank 0x68, renderer in 0x6a, work in 0x6b, staging in 0x6c, and selected gameplay/overlay code in other 8 KiB windows. Banks 0x76 and 0x77 are CD transfer scratch and may not contain code that remains live through a loader call. Audio control/sample paths have their own banks; Ramrod's arena can replace selected code banks with code images read from the stage archive. A resident trampoline restores the old MPR mapping after nested calls.

The game also divides VRAM among BAT, background cache, font/dialogue tiles, sprite patterns, clipped-sprite storage, and SAT. Its background cache reserves held slots until VBlank removes the last visible BAT reference. The final 128 KiB of its Arcade Card address space is a tile lookup directory. These reservations are described in Saber Rider's pce_config.h and PCE_PORT.md, not in the LLVM-MOS ABI.

## Procedure for a new project

1. Build once with map/runtime reports enabled. Record each load region, capacity, used bytes, and alignment from tool output.
2. Mark roots that must remain mapped: IRQ vectors, IRQ bodies, stack, resident loader, and return trampolines.
3. Mark lifetimes for scene data, transfer scratch, overlays, sprite/cache entries, sound samples, and temporary conversion buffers.
4. Permit reuse only after proving no return address, interrupt, pointer, DMA, SAT generation, or live BAT entry still refers to the region.
5. Run the linker-report helper to rank candidate banks, then inspect relocations, section placement, overlay call graph, and live data before moving code.
6. Rebuild and inspect the new map/report. Measure runtime capacity from the built image, not old notes.

The included bank_space.py tool ranks reported headroom. It cannot prove overlay safety or that a bank may be reused. Follow [bank placement and safe relocation](../../references/banks-and-overlays.md) before moving a routine.
