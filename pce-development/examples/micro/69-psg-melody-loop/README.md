# 69-psg-melody-loop

**Category:** Audio

Loop a four-period melody on PSG channel 0 with approximate CPU delays.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
