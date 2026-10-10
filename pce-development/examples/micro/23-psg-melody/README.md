# 23-psg-melody

**Category:** Audio

Play three notes on PSG channel zero, changing only the pitch register.

Build with `make`; the output is `build/23-psg-melody.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Timing:** Busy-loop waits are approximate and not suitable for precise music, PCM sample rates, or production raster effects.
