# 84-arcade-card-independent-ports

**Category:** Arcade Card

Verify port 0 and port 1 have independent address counters.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
