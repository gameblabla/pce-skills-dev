# Bank space and safe code relocation

Use this guide when the LLVM-MOS linker reports that a banked code section
does not fit. A bank with free bytes is only a capacity candidate. Relocation
is safe only when code placement, every mapped caller, live data, interrupts,
and runtime bank use remain correct.

## Inspect the current LLVM-MOS build

From the active project root, inspect build instructions, dirty files,
linker script, bank/section declarations, overlay trampoline, generated ELF,
map, and any machine-readable runtime report. Search code and linker files for
section attributes, bank macros, MPR writes, overlay calls, callback tables,
and loader/audio/raster paths.

Use the bundled Python helper to rank a fresh report:

```sh
python3 scripts/bank_space.py PATH/TO/runtime.json --needed REQUIRED_BYTES
python3 scripts/bank_space.py PATH/TO/runtime.json --needed REQUIRED_BYTES --exclude 0x76,0x77
```

The bank identifiers above are only syntax examples. Replace them with banks
confirmed as reserved in the active project. If the report lacks a `banks`
array, provide its per-bank capacity explicitly; do not assume every project
uses the same bank size/layout. Use `scripts/calc.py` for byte/address math.

The helper ranks capacity only. It cannot determine temporal reservations,
call safety, or data lifetime.

## Trace dependencies before choosing a destination

For the selected function and its helpers, inspect:

1. The explicit LLVM-MOS section attribute/macro and all code/rodata/data
   emitted into its bank after optimization/LTO.
2. Direct and indirect callers, including overlay wrapper macros, callbacks,
   function-pointer tables, interrupt vectors, and assembly references.
3. The bank/MPR mapping at entry, every nested call, and return. A pointer
   contains a CPU address, not the physical bank that supplies its bytes.
4. Static tables, literals, jump tables, compiler helpers, and data ownership.
   Code can move while a large constant remains behind in the full section.
5. The trampoline, return path, stack, IRQ routines, loader state, and any
   callback that must remain mapped during execution.
6. Any bank used as a CD transfer window, audio/sample mapping, decompression
   scratch, work memory, or temporary scene storage. Reject a destination if
   that use overlaps the function's execution lifetime.

Treat a known temporary reservation as unavailable by default. Reuse it only
after source/runtime evidence proves the reservation interval cannot overlap
any code, data, caller, IRQ, or callback lifetime that depends on the bank. If
the intervals or lifetime are unknown, keep the bank excluded; a free-byte
report cannot establish that they are disjoint.

If the project uses an overlay trampoline, preserve its save-map-call-restore
contract and nested-call behavior. Keep a pointer into banked code or data only
while the correct MPR maps it. Never call a routine in an overlay directly
unless the current mapping is proven to contain that routine.

## One relocation at a time

1. Record pre-edit map/report and caller sites; preserve unrelated edits.
2. Move the smallest coherent routine group and its owned constants when
   appropriate. Update its LLVM-MOS section annotation and all bank-aware call
   sites together.
3. Build with the pinned `mos-pce-clang` and matching LLVM-MOS linker. Read
   the new map/ELF report; check source and destination capacity.
4. Run a focused emulator case reaching every caller, nested overlay, return,
   scene transition, and overlapping loader/IRQ/audio path.
5. Inspect generated assembly/map and the diff. A successful link alone does
   not prove runtime safety.

## Report the decision

When explaining a full-bank fix, make the decision sequence explicit:

1. Name the `bank_space.py` ranking as capacity evidence and identify which
   candidates meet the section size. The helper result is Python output; do not
   re-evaluate its arithmetic or treat its ranking as a safety verdict.
2. Exclude every candidate with a known overlapping runtime reservation. If
   timing/lifetime is unproven, keep it excluded and inspect another candidate.
3. Trace mapped callers, the overlay save/map/call/restore path, constants and
   tables, stack, IRQs, and any banked data used by the moved code.
4. Only then move a cohesive section, rebuild with the pinned LLVM-MOS PCE CD
   toolchain, inspect the new link/map/ELF report, and run a focused emulator
   regression through all relevant callers and overlapping loader/IRQ paths.

Do not report a completed relocation or safe destination before those gates
pass.

The complete example is in [`examples/12-bank-relocation/README.md`](../examples/12-bank-relocation/README.md).

## Frequent misses

- LTO, constants, or helper emission makes the final section larger than the
  source code looked.
- The routine moved but a caller still maps the old physical bank; the pointer
  now reaches unrelated bytes at the same logical address.
- The linker shows free bytes in a bank that the CD loader overwrites during
  transfer or the audio timer maps while playing.
- A moved function still reads tables left in a bank that is no longer mapped.
- A change fixes one overlay but breaks another caller sharing the destination.
- The test exercises only one scene/call path or never reached the intended
  runtime state.

No commit history or chat transcript is required to apply this procedure.
