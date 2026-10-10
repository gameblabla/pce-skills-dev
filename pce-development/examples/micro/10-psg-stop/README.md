# 10-psg-stop

**Category:** Audio

Start a tone, then explicitly stop it, without turning on display hardware.

Build with `make`; the output is `build/10-psg-stop.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Timing:** Busy-loop waits are approximate and not suitable for precise music, PCM sample rates, or production raster effects.
