# 49-timer-irq-stop

**CPU/IRQ:** Stop the timer after 100 IRQ callbacks; no VBlank or video dependency.

Inspect the `volatile` variable(s) with an emulator debugger; the ROM intentionally draws no status UI.

Build with `make`. Run with `make run` or `make debug` (the shared wrapper configures the emulator). HuCard target; optional expansion hardware is noted by the example name.
