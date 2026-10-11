# VCS height converter adapted to PCE paired-BAT bitmap

Original reference: Guillaume Laudet, *Realtime Raycasting on the Atari VCS*
(2018), supplied as `vcs-demo-raycaster-master.zip`. The source files and MIT
license are preserved under `pce-development/third_party/vcs-raycaster-reference/`.

## What actually transfers

The VCS raycaster separates ray intersections from a *height-threshold
converter*: after computing min/max wall heights, a row of the display
consumes preclassified wall coverage. The VCS implementation packs two
heights into a byte and uses packed precomputed bit patterns to build TIA
playfield bytes, then XOR-delta encodes adjacent rows for its 128-byte RAM.

The PCE version keeps the existing 128 independently sampled ray directions,
32x32 near-wall textures, and PCEdev paired-BAT VRAM layout. For **each pair
of wall pixels**, `stage_pair_words` computes four height transitions:
`left_top`, `left_bottom`, `right_top`, `right_bottom`. Its converter traverses
at most five coverage spans, using specialized loops for `00` (background),
`01` and `10` (one wall), and `11` (both walls). The `11` loop never looks up
the backdrop and none of the loops rechecks wall visibility per pixel. The
resulting 16-bit BAT words use the same palette, textures and rotated second
page as the previous version, and the staged VBlank uploader is unchanged.

This is a **conceptual adaptation**, not a binary transplant of the Atari
assembly. The original assembly is included for study and attribution.
`-DRAY_VCS_SPAN_CONVERTER=0` restores the previous C converter for exact
independent ROM comparisons. For per-routine master-clock profiling, build
both versions with `-DRAY_PROFILE_STAGE_WORDS=1` to keep the function boundary
uninlined in both binaries.

## Equal-work emulator evidence

An equal-controller 1,080-video-frame benchmark after warm-up showed **14
completed dirty-view passes** and **1.5 turning dirty-view commits/second**
for both old and new rendering paths, with the same 60,281 VRAM BAT words.
A stationary 600-frame screenshot comparison found **zero differences out
of 135,520 RGB pixels**. Raster sweep (540 frames) and movement stress
(1,080 frames) also passed on the VCS-span build.

A separate pair of equally instrumented builds, each forcing `noinline`
for the same stage function, measured these **self-attributed master ticks
per video frame**, not whole-program FPS:

| Segment | Previous converter | VCS-span converter |
|---|---:|---:|
| Turning | 122,465 | 76,766 |
| Walking | 150,720 | 86,839 |

That is approximately 37% less compositor time during turning and 42% less
during walking in this instrumented comparison. No increase in completed
view throughput has been established. Raster IRQs and the fixed 96-word
safe VBlank upload cap continue to limit visible redraw speed, and console
hardware performance is unverified.

To reproduce geometry/source tests: `python3 -m unittest
pce-development.workflows.tests.test_vcs_span_converter` from the repo root.
The emulator comparison is `make -C
pce-development/examples/34-rendered-raycaster vcs-span-check` with
`PCE_HEADLESS` and LLVM-MOS configured.

Machine-readable benchmark, raster and profiler summaries are retained in
[`vcs-span-evidence.json`](vcs-span-evidence.json). These can be checked
against the independent ROM builds rather than treating raw CPU idle time as
an FPS measurement.
