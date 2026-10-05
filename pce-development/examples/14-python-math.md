# Example 14: calculate with Python

When this calculation workflow is used while creating or changing project
code, follow the [shared starter Makefile contract](README.md#recipes) so the
project bootstraps and exports LLVM-MOS consistently.

Whenever a task needs arithmetic, run the helper instead of asking the model
to do it mentally. This includes bank free space, transfer sizes, sector
extents, fixed-point conversions, sprite budgets, tile totals, offsets, and
cycle budgets.

From the skill directory:

```sh
python3 scripts/calc.py '50 * 1888'
python3 scripts/calc.py '($7C - $68) * 8192'
python3 scripts/calc.py '(640 * 224) / 8'
```

The helper accepts integer arithmetic, exact division, powers, shifts,
bitwise operations, parentheses, decimal/hex/binary literals, and `$`-prefixed
hex values. It parses a restricted AST; it does not execute Python expressions
or function calls.

For a current linker report, rank candidate capacity with:

```sh
python3 scripts/bank_space.py PATH/TO/runtime.json --needed REQUIRED_BYTES --exclude 0x76,0x77
```

The report tool never picks a safe overlay. After it returns, inspect project
reservations, mappings, callers, data lifetime, and the post-link map using
[`12-bank-relocation.md`](12-bank-relocation.md).

For fixed-point work, write down the scale and units first, then use Python to
convert boundary values and confirm rounding/overflow cases. Keep runtime
expressions in C/assembly only after calculation and bounds are reviewed; the
helper is for reasoning and validation, not a replacement for correct target
arithmetic.
