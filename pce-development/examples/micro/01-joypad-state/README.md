# 01-joypad-state

**Category:** Input

Read the active-low joypad and store pressed buttons. Nothing is drawn.

Build with `make`; the output is `build/01-joypad-state.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.
