# 24-psg-noise-sweep

**Category:** Audio

Change noise divider on PSG channel 5 without relying on visuals.

Build with `make`; the output is `build/24-psg-noise-sweep.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Timing:** Busy-loop waits are approximate and not suitable for precise music, PCM sample rates, or production raster effects.
