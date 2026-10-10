# 04-psg-sweep

**Category:** Audio

Sweep one PSG tone. CPU delays are approximate, not accurate note timing.

Build with `make`; the output is `build/04-psg-sweep.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Timing:** Busy-loop waits are approximate and not suitable for precise music, PCM sample rates, or production raster effects.
