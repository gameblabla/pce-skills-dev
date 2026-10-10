# 05-psg-stereo

**Category:** Audio

Alternate sound balance left/right on a single PSG tone.

Build with `make`; the output is `build/05-psg-stereo.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Timing:** Busy-loop waits are approximate and not suitable for precise music, PCM sample rates, or production raster effects.
