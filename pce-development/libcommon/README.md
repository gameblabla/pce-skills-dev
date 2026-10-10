# libcommon: narrow arithmetic for the HuC6280

`include/pce_fastmath.h` provides exact 8x8 products, signed 8x8 products, an
unsigned 16/8 division fallback and truncating signed shifts. These use only
8/16-bit integer operations; **there is no claim the generic long-division
fallback beats an optimized runtime helper**. Use the specialized lookup path
for hot loops.

`pce_mode7_axis()` is the fast path for the BAT-backed 512x224 pseudo-bitmap
lesson: five coefficient tables generated offline from the 16 camera angles
and 93 perspective depths, with no target-side multiplication or division.
The old version linked `__mulhi3` and `__divhi3`; the optimized target should
link neither. Re-generate by running `python3 tools/gen_mode7_lut.py`, then
`make tables-check`. Files are plain C and are built as `build/libpcecommon.a`.

This is LLVM-MOS: integer helpers such as `__mulhi3`/`__divhi3` come from the
**LLVM-MOS runtime/compiler-rt**, not from GCC `libm`. `libm` implements floating
math functions such as `sin` and `cos`, and should never be needed for these
ROMs. Validate both the C source and the final ELF, not just `-lm` flags.

For large source maps, bank addresses or trace wire formats, wider values may
be unavoidable. They are *existing audited compatibility exceptions*, not
permission to introduce 32/64-bit arithmetic in new gameplay code.

`pce_circle_radius()` uses a 40-byte offline-generated lookup to replace two
squaring multiplies per pixel in example 85. It retains the exact inequality
`x*x+y*y < 1600` while removing target-side multiply from the inner loop.

`make arith-audit-all` from the repository root verifies every micro ROM has
no compiler software multiply/divide in the final ELF. Existing complex
P2TR/G2TR projects have source-level frozen exceptions; they are *not* yet
covered by a strict linked-ELF audit.
