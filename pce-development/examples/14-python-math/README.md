# Example 14: calculate with Python

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/14-python-math.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

When this calculation workflow is used while creating or changing project
code, follow the [shared starter Makefile contract](../README.md#projects) so the
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
[`12-bank-relocation/README.md`](../12-bank-relocation/README.md).

For fixed-point work, write down the scale and units first, then use Python to
convert boundary values and confirm rounding/overflow cases. Keep runtime
expressions in C/assembly only after calculation and bounds are reviewed; the
helper is for reasoning and validation, not a replacement for correct target
arithmetic.
