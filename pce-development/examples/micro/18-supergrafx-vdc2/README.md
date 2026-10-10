# 18-supergrafx-vdc2

**Category:** SuperGrafx

Initialize and address SuperGrafx VDC2, then switch back; no compositing claim.

Build with `make`; the output is `build/18-supergrafx-vdc2.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Hardware:** Real SuperGrafx hardware (or correctly configured emulator) is required for VDC2 operations.
