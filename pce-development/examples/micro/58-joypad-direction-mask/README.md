# 58-joypad-direction-mask

**Category:** Input

Keep only the four D-pad direction bits in a debugger-visible byte.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
