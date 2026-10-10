# 19-arcade-card-detect

**Category:** Arcade Card

Read Arcade Card identification byte; works without graphics or disc.

Build with `make`; the output is `build/19-arcade-card-detect.pce` (HuCard). This single-file example uses the local LLVM-MOS PCE SDK. There is deliberately no screen initialization or text; inspect the `volatile` variable in a debugger if one is declared.

**Hardware:** Arcade Card-specific RAM does not exist on a plain HuCard console; this is a probe, not a guaranteed facility.
