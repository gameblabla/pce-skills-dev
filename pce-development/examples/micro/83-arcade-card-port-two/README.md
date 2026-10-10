# 83-arcade-card-port-two

**Category:** Arcade Card

Access Arcade Card RAM through data port 2 at 0x1a20.

HuCard ROM: `make`; headless smoke test: `make run`. Inspect `volatile` results in an emulator debugger where applicable. Audio timing from `pause_cpu` is intentionally approximate; no screen or text is initialized for audio, CPU, controller or Arcade Card examples.
