# 71-psg-reload-wave

**Category:** Audio

Turn off PSG channel 0, reload 32 waveform samples, then restart playback.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
