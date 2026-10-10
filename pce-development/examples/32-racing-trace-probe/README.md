# Racing — G2TR v2 instrumentation probe

This tiny HuCard publishes a **genre-specific telemetry record**, not a playable game and not a rendered demonstration. It intentionally has no graphics or text code. Its state fields are documented in `tools/genre_trace.h`.

Build with `make`. Set `PCE_HEADLESS` to an emulator with `run`, `input` and `memread` RPC, then run `make trace` to capture a 48-frame real emulator trace. Validate source/input/gameplay separately for a real game. See `../../tools/pce/GENRE_TRACE.md`.
