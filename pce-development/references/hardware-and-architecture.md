# PC Engine hardware with the LLVM-MOS PCE CD target

This skill targets PC Engine/TurboGrafx-16 software through LLVM-MOS only. The
HuC6280 is the console CPU and instruction set; that name describes hardware.
Use the active project's pinned `mos-pce-clang`, LLVM-MOS integrated
assembler, linker scripts, SDK headers, and CD image tools as a matched set.
Keep every C, inline-assembly, and `.S` implementation within this toolchain.

The exact ABI and supported instruction spelling can change with the pinned
LLVM-MOS version. Check that version's official PCE target documentation,
generated disassembly, and compiled test image. Hardware manuals describe the
CPU/VDC behavior; they do not define the LLVM-MOS source syntax.

## CPU and address mapping

The HuC6280 presents a logical address space through Memory Page Registers
(MPRs). The PCE CD target can map internal/CD/Arcade RAM into CPU-visible
windows, but the active project's linker script and startup code decide which
physical banks appear where. Read those files and the generated ELF/map before
assuming an address refers to a particular storage bank.

When code remaps a window, keep the executing return path, stack, IRQ entry,
callback, and live data mapped. An overlay trampoline should save and restore
the prior MPR state. A function pointer carries an address, not its physical
bank. Keep pointers to banked data within the mapping lifetime and avoid
returning a pointer into a bank that is unmapped or reused.

The target ABI controls `int`, pointer, calling convention, zero page, and
interrupt attributes. Verify with the pinned compiler and static assertions;
do not copy width assumptions from a host build or another compiler.

## LLVM-MOS implementation rules

- Compile C with the PCE CD target driver from the same LLVM-MOS installation
  as its headers, libraries, assembler, linker, and CD image tools.
- Keep target-specific C/assembly syntax within LLVM-MOS. For hand-written
  assembly, use the integrated assembler accepted by the installed target.
- HuC6280 block moves are hardware instructions. Confirm that the pinned
  LLVM-MOS assembler accepts their mnemonic/operand form. If a target version
  requires byte encodings, label the encoding and verify it against the opcode
  reference and generated disassembly.
- Inspect emitted assembly/disassembly for MPR writes, interrupt prologues,
  register preservation, helper calls, and code placed in banked sections.
- Keep compiler/linker/assembler versions fixed for reproducible builds.

## Video, sprites, and VRAM

The PCE uses one VDC background plane and one sprite system. Arcade Card RAM
adds storage and transfer ports; it is not a second background plane, general
scaler, alpha blender, or extra sound chip. Design effects around the VDC, VCE,
SAT, BIOS CD audio/ADPCM, and PSG paths actually available to the target.

Treat VRAM partitioning as a project-owned layout. Account for BAT, background
patterns, sprite patterns, SAT, fonts, clipping/blank patterns, and temporary
upload destinations. Verify address units at each API boundary; VDC word
addresses are easy to confuse with byte offsets. A source asset preview is not
proof that the generated runtime patterns, palettes, and BAT agree.

The sprite system has finite SAT entries and a per-scanline capacity. Keep
admission priority deliberate: essential actors and hazards before optional
shots and effects. A refused projectile must not cause invisible damage. Use
the active display mode and hardware limits in emulator tests.

Scrolling and cache ownership need a publication boundary. A leaving BAT
column or its patterns may remain visible until VBlank. Do not recycle a slot
as soon as CPU-side references change if the displayed frame still names it.
Publish matching background scroll and SAT state together.

## VBlank/HBlank and transfer timing

Read the SDK's interrupt entry/return convention and compiler attributes for
the specific IRQ. Do not paste a generic 6502 ISR into an LLVM-MOS PCE handler.
Preserve every register, MPR, stack, and VDC index value required by the calling
convention.

Treat VDC address selection plus data writes as one short transaction if an
interrupt can change the selected register. Keep only the necessary setup
atomic. Split large Arcade Card, SAT, HUD, and VRAM transfers into bounded
chunks so time-sensitive IRQs can run between them. Derive the maximum chunk
from measured worst-case IRQ deadlines for the current video mode, and use
Python for cycle/byte arithmetic. Do not copy a burst size from another
project as a universal constant.

For one-row glitches with stable input tables, measure interrupt assertion,
latency, interrupted work, and the precise VDC write relative to the latch.
Audio setup, a block transfer, or a display copy may be the source of the
delay even when the renderer's data is correct.

## Number and performance discipline

The PCE is an 8-bit CPU with a project-specific LLVM-MOS ABI. Give fixed-point
values named units and a documented scale. Check signedness, overflow, shifts,
rounding, division, and worst-case products at the target width. Use
`scripts/calc.py` for every calculation and inspect the generated code for
expensive compiler helpers. Avoid floating point in time-critical paths unless
the compiled implementation and budget are explicitly verified.

Optimize measured hot paths. A passing link does not prove timing, and a
frame-rate claim must count completed presentations over video frames for a
named scenario. Keep emulator and physical-hardware evidence separate.
