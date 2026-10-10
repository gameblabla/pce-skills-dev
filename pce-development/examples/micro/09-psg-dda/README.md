# 09-psg-dda

**Category:** Audio

Direct PSG DAC writes at CPU speed; no 60 Hz screen updates. This is a pitch/timing demonstration, not stable sampled-audio playback.

Build with `make`; the output is `build/09-psg-dda.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.
