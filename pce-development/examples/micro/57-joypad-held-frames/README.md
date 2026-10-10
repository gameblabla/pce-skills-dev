# 57-joypad-held-frames

**Category:** Input

Count consecutive controller polls while LEFT is held (not real frames).

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
