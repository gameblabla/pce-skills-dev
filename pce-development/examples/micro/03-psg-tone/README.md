# 03-psg-tone

**Category:** Audio

Continuous PSG tone on channel 0; no VDC, VCE, fonts or graphics.

Build with `make`; the output is `build/03-psg-tone.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.
