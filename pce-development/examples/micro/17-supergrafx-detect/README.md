# 17-supergrafx-detect

**Category:** SuperGrafx

Check for extra VDC hardware; no video output or compositing is attempted.

Build with `make`; the output is `build/17-supergrafx-detect.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Hardware:** Real SuperGrafx hardware (or correctly configured emulator) is required for VDC2 operations.
