# 20-arcade-card-port

**Category:** Arcade Card

Write/read eight bytes via Arcade Card port zero with proper 16-bit offset setup. Requires Arcade Card.

Build with `make`; the output is `build/20-arcade-card-port.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Hardware:** Arcade Card-specific RAM does not exist on a plain HuCard console; this is a probe, not a guaranteed facility.
