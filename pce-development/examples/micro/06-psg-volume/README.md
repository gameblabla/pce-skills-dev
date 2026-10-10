# 06-psg-volume

**Category:** Audio

Fade a PSG tone with the 5-bit channel amplitude control.

Build with `make`; the output is `build/06-psg-volume.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Timing:** Busy-loop waits are approximate and not suitable for precise music, PCM sample rates, or production raster effects.
