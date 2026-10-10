# 21-timer-irq

**Category:** CPU/IRQ

Tick a volatile counter from the CPU timer IRQ; no video wait.

Build with `make`; the output is `build/21-timer-irq.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.
