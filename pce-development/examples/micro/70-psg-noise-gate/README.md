# 70-psg-noise-gate

**Category:** Audio

Gate noise on and off using channel 5 noise enable, leaving display untouched.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
