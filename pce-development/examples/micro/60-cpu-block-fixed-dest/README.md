# 60-cpu-block-fixed-dest

**Category:** CPU

Use TIN to repeatedly overwrite one RAM byte; its final value is the last source byte.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
