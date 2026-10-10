# 00-cpu-loop

**Category:** CPU

Minimal C entry point; no video, sound or peripheral initialization.

Build with `make`; the output is `build/00-cpu-loop.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.
