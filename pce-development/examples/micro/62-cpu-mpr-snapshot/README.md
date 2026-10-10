# 62-cpu-mpr-snapshot

**Category:** CPU

Read MPR2, MPR3 and MPR4 mappings without altering bank registers.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
