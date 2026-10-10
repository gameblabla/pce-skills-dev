# PC Engine development skill bundle

Start with [`pce-development/SKILL.md`](pce-development/SKILL.md). The skill
and examples are self-contained: do not assume a sibling game repository,
private BIOS, compiled emulator binary, or conversation export is present. The
bundle includes licensed headless source under `pce-development/third_party/`;
preserve its upstream and component license notices.

Do not put an emulator executable's name into a local coding-agent prompt or
ask the agent to launch one directly. Project `make run`, `make debug`, and
`make trace` targets select the configured headless frontend and own its
arguments. `make bios-check` prints the user-local placement folder when CD
firmware is absent.

For platformer work, read
`pce-development/references/platformer-rules.md` and
`pce-development/examples/25-platformer-integration/README.md`. Keep physics in
world coordinates, trace real collision and render state with P2TR v1, and use
deterministic `make trace` scenarios to check walking, gravity, landing, and
camera behavior even when the local model cannot inspect images. A text report
does not establish pixel appearance or physical-console behavior.

The bundle has an arithmetic helper at
`pce-development/scripts/calc.py` and a linker-report capacity ranker at
`pce-development/scripts/bank_space.py`. The ranker does not prove that a bank
can be safely reused; follow
`pce-development/references/banks-and-overlays.md`.

Run the local model evaluation from this directory:

```sh
python3 pce-development/scripts/eval_local_ai.py
```

Read `pce-development/scripts/README.md` for evaluation options and limits.
Run `python3 pce-development/examples/micro/check.py --lint-only` to guard
sound-only versus graphics-only examples when changing them. The category
is explicit in each README; use `--self-test` to verify mixing is detected.
Run `--smoke` with Pillow and the configured headless frontend to assert
audio renders a blank display and a sprite graphics sample is visible.

Use `pce-development/examples/` for project recipes; each recipe identifies
where SDK-specific adaptation is required. Scratch projects copy the starter
Makefile and tools, then select the LLVM-MOS driver for the requested HuCard or
CD target. The shared PCE image/font/sprite converters, audio encoders, BIOS
ADPCM player, and SoftADPCM/DDA decoder library are documented in
`pce-development/tools/pce/README.md`. These tools contain no game-specific
art, ROM, BIOS, or archive data.

## Offline game-request router (for Luna / Leading Edge / smaller local models)

Before inventing a new game/physics scaffold, run `python3 pce-development/workflows/offline.py route "USER REQUEST"` and follow its concrete recipe. For a simple playable platformer choose example 26; for explicit platformer + racing segments choose example 27 with its generated `hybrid_rules.h`. Read `pce-development/workflows/README.md` and the generated project's README. Do not mix their stage-specific X/Y coordinates, and do not treat host-side simulation as game execution. Enforce one scene owner at a time, and test entry and return transitions. `make test` runs offline unit/static checks; `make hybrid-test` needs a newer RPC-capable emulator. **Never claim a failing P2TR scenario succeeded on a prebuilt emulator without `trace_frames`.**

The user-provided transcripts are private inputs for deriving incident patterns only; they are not part of the redistributable toolkit. A separate `transcript_lessons.py` reports aggregate categories without copying their text. Keep them outside commits and published archives.

## Additional Luna / local-AI failure gates

Four later sessions exposed hallucinated joypad/sprite API names, hand-counted array overruns, linker/vector overflows, GUI emulator timeouts mistaken for gameplay success, and .pce builds mistaken for a Super CD disc. **Before writing a large game**, follow `pce-development/references/local-ai-transcript-fixes.md`, run `offline.py route` with the complete user request, then use the new `model_guard.py scan` and `assetpack.py --check` commands. In existing game starters `make model-check` runs before the build. `make diagnose LOG=...` maps common errors to actions; `make acceptance-check` deliberately fails until distinct evidence exists. For a JSON tilemap to real 4bpp VDC graphics, use standalone `examples/28-generated-level`. Do not claim that its entity metadata is playable enemies. Use `make agent-check agent-assets agent-build` at the root.

## Cross-genre P2TR/G2TR and visual-novel work

Never reuse `P2TR v1` collision-surface fields for unrelated genres. Keep platformer P2TR v1 (216 bytes ×2); use the new `G2TR v2` (64 bytes ×2) and genre-specific validators for shmup, racing, raycaster or visual novel. Run `make genre-check` first (no SDK), then `make genre-build`, `PCE_HEADLESS=... make genre-test` when RPC and compiler exist. `trace_frames` in the bundled emulator only accepts P2TR v1; the generic runner uses `run`+`memread` instead. A RAM trace is game-authored data, not evidence of pixel output.

For visual novels, do not hand-code huge picture arrays: use `examples/29-visual-novel/tools/vn_pack.py` and versioned PNGs. Single-palette generator only requires Pillow; multi-palette fitter requires NumPy too. Use generated BAT/4bpp patterns for background and SAT 16x16 pattern indices for mouth overlays. Check the manifest for ROM/VRAM/palette constraints and `make visual-test` for actual mouth-only screenshot differences. Avoid making a visual-novel sprite depend on sound/text raster init unless requested.

## Rendered genre examples and screenshot acceptance (33–35)

After choosing a genre with `offline.py route`, prefer rendered example 33
(shmup), 34 (raycaster), or 35 (conventional racer) when visual output is part
of the request. Preserve examples 30–32 as intentionally **nonvisual** G2TR
instrumentation probes. For true 512×224 pseudo-bitmap road rendering, use
micro example 86 rather than calling the fixed perspective racer Mode 7.

For 33 and 35, change PNGs and run `make assets` instead of hand-writing huge
C graphics arrays. `tools/scene_pack.py` validates indexed colours, a 64×16
sprite strip, tile counts and VRAM allocation. For 34, raycast actual map cells
and submit the height columns to the VDC BAT; do not substitute a static image
and claim that it is a raycaster.

Run `make trace` **and** `make visual-test` for each rendered project. The first
checks game-authored G2TR telemetry under scripted input; the second captures
and compares actual emulator pixels, input latching and screen-space motion.
Neither proves physical hardware performance, audio or complete game mechanics.
The basic `pce_joypad_read()` returns **eight bits** (two-button controls); do
not invert it into `uint16_t` and interpret the high nibble as extra buttons.
Initialize mutable gameplay globals explicitly in `main()` for minimal HuCard
startup environments; do not assume initialized `.data` was copied as on a PC.
See `pce-development/tools/pce/GENRE_TRACE.md` for the trace contract.


## Interaction-complete testing and hardware sprite budgets

Rendered movement is only the first gate. For a request involving combat,
projectiles, blocked movement, checkpoints, laps or crashes, use the projects'
`make interaction-test` **before** claiming gameplay works. It records the
full decoded G2TR timeline (`build/interaction-frames.json`), and
`make interaction-replay` runs offline assertions over those records. Preserve
short collision/checkpoint event latches so the RPC sampler cannot skip a
single-frame pulse. Ensure a required event is provably triggered by scripted
input, not just present in a manually constructed trace. Run `make visual-test`
separately to confirm a changed framebuffer; G2TR is game-authored state.

Before increasing actors or SAT sprites, run
`python3 pce-development/workflows/sat_budget.py YOUR-SAT-SPEC.json --strict`.
This handles the 64-entry and 16-per-scanline VDC limits, prioritizes essential
actors, and supports two independent SuperGrafx VDCs. Use the ordered accepted
list for the game's SAT, not the unsorted source list. Read
`pce-development/references/interaction-and-sat-verification.md`.

## Arithmetic policy for new game code

Always run `make arith-check` before integrating target-side math and
`make arith-build` after edits to the BAT-backed examples. Do not introduce
32/64-bit or floating C data in new HuC6280 gameplay, or link `-lm`/`-lgcc`.
Keep explicit 8/16-bit world representation (use Q4 for 512-pixel camera
ranges, Q8 for bounded short offsets), and wrap on purpose. Precompute trig,
reciprocals and perspective depths offline into `libcommon` rather than
allowing the linker to pull in `__mulhi3`/`__divhi3`. The frozen compatibility
manifest must not be enlarged automatically to silence a warning. A user
request for true 24-bit Arcade Card addresses or P2TR/G2TR 32-bit wire fields
needs reviewed narrow byte/word helpers or an explicit, justified exception.

## Raster-safe upload budgets and narrow genre math

For new graphics streaming, first create a JSON plan matching
`pce-development/workflows/specs/vram-streaming.json` and run:

    python3 pce-development/workflows/vram_budget.py PATH_TO_PLAN.json --strict

Layout uses VRAM **words** (0..0x7fff) but upload sizes are **bytes**.
A budgeted transfer is not evidence that timing succeeds on real hardware.
If raster interrupts are active, split TIA/TAI into <=16-byte bursts with
interrupts allowed between them; never claim a long block transfer is safe.
By default, do not write visible BAT rows outside a documented VBlank
publication step. The fast full-detail raycaster is an explicit exception:
progressive *visible* BAT edits use the VDC +128-word vertical stride and
no more than 16 bytes per interrupt-masked burst, restoring interrupts between
bursts. Such edits may tear. Require a documented `progressive_visible` VRAM
budget and a long emulator input/screenshot stress test; never call that atomic.

Before submitting rendered racing, shmup or raycaster projects run
`make arith-games` and `make genre-test` with the input-capable emulator.
For the raycaster use `tools/gen_ray_tables.py` to precompute signed ray steps
on the *host*. Never reintroduce per-column `/40`, `/5` or `*side` expressions
into its HuC6280 render loop. For parallax race traffic prefer bounded 8-bit
phase+remainder accumulators, not divide and modulo each frame.
`make performance-check` performs the offline checks; `make arith-games`
verifies actual linked ELF symbols. P2TR/G2TR ABI 32-bit fields are not a
license to use 32-bit arithmetic in new gameplay. No unmeasured FPS claims.

For `scene_pack.py` projects, run `python3
pce-development/workflows/scene_vram.py pce-development/examples/33-rendered-shmup`
(or the relevant project). It validates generated tile/sprite array sizes
against the scene manifest and boot transfer budget, rather than trusting a
hand-written VRAM JSON plan.

## Current platformer mandate (supersedes old P2TR and Q8 instructions)

Use example 26 or 27 with `platformer_q4.h` and `P4TR v4` for NEW platformer
projects. The two portable projects have no wide runtime integer variables, no
software mul/div helpers, and only 64 trace bytes. Do not copy obsolete P2TR
v1 / 32-bit Q8 examples unless examining history. `make platformer-check` is
host-only and must pass before building; `PCE_HEADLESS=... make platformer-test`
proves actual movement/landing and continued gameplay following a racing scene
handoff. A screenshot of the return scene is not a valid proof of continuation.
Do not re-run `demo_video_init()` on every scene handoff. Prefer a background
restore and bounded per-frame VDC word writes for SAT entries. Validate the
screen separately from RAM telemetry. `make arith-games` audits the linked
platformer ELFs in addition to the shmup, racer and raycaster.

## Mandatory measured cycle profiling before performance claims

**Do not call emulator video frames CPU frame rate.** For changes touching
raycaster bitmap pixels, Mode 7 sampling, IRQ code, fast math, collision or
platformer motion, run `make cycles-check` (offline) and use an RPC-capable
headless emulator with `PCE_HEADLESS=/path/to/pce-headless make cycles-all`.
The CPU core exposes physical HuC6280 **master-clock timestamps** via
`prof_start`/`prof_dump`. `workflows/cycle_profile.py` attributes them using
linked `.mlb` *physical ROM offsets*, not logical CPU program counters.

Use `build/cycles/*/report.json` and `report.md` to find actual bottlenecks.
Use the reported `game_updates` and `updates_per_emulator_frame` to detect
rendering that keeps VBlank running while barely updating gameplay.
Run `make cycles-ray` to enforce interrupt, wall pixel and casting budgets.
Never claim a speedup based on a lower overall frame total (the frame's
master-clock budget is fixed), or on lower `main` cycles after an inlined
routine was split into a separate symbol. `cycle_profile.py compare` refuses
a per-function comparison if the old/new ROMs complete different game update
counts under the same scripted input. Matching counts alone are not hardware
verification: inspect scene state and screenshots separately.

The older C-IRQ 512x224 raycaster spent over half its measured emulated
master-clock time servicing raster IRQs; the native IRQ cut that cost,
but the raster work remains substantial and the game loop still runs
less often than the emulator video frames. Do **not** blindly use `noinline` on the inner bitmap
slice writer to make a prettier profile: a compiler/timing variant caused
intermittent incomplete frames. The current working renderer keeps that loop
inline, preserving the existing bitmap, rotation and collision tests. If a
profiling change modifies output, reject it even if the profiler is cleaner.
Hardware stopwatch/logic-analyzer measurements remain a separate requirement.

## Paired-BAT raster IRQ performance policy

For 512x224 BAT-backed bitmap examples, use the **opt-in** native
`libcommon/src/bat_bitmap_irq.S` (Mode 7) or the identical vendored
`34-rendered-raycaster/src/bat_bitmap_irq.S`. Never link a strong
`irq_vdc` by default into audio-only examples. The native assembly must
save/restore A/X/Y, finish with RTI, and publish `.type` + `.size` so
cycle attribution covers the complete function. Keep the safe per-physical-
scanline comparator schedule: experimentally skipping raster events made the
raycaster occasionally render sky-only during sustained rotation.

After changing video timing or SAT/BAT updates, run `make test`, the
raycaster's `make visual-test` and `make interaction-test`, Mode 7's smoke
capture, and `make cycles-ray` / `make cycles-all`. Reject faster versions
with blank/incomplete frames. Report emulator *master ticks per frame* and
game-update counts separately, and don't call per-routine before/after
costs comparable when the counts of completed updates differ.

## Mandatory BAT publication / completed-redraw acceptance

The 512x224 textured raycaster now transfers **8 logical BAT rows / game
update**, with **one 128-byte HuC6280 TIA** per logical row, during VBlank.
`TIA` alternates the destination byte ports `$0002/$0003`, so the VDC data
word advances correctly. Keep the ordinary raster IRQ active during display,
but do NOT begin long active-display TIA bursts; they mask interrupts.
`make raycaster-throughput` builds an independently instrumented 4-row TIA
comparison ROM, checks six actual emulator screenshots per ROM, counts
completed 128-row BAT passes (post-upload, not G2TR updates), and rejects
a throughput regression or incomplete/sky-only view. The measured six-stage
scenario completed 10 vs 16 passes in 1,080 identical emulator frames;
**that is redraw throughput, not a 60 FPS claim**. Each frame may show a
progressive partial redraw. Do not claim atomic image swaps.

For physical BAT address planning, logical rows 0..63 map to words
`row*128`, and logical rows 64..127 map to words `((row&63)*128)+64`.
`workflows/specs/raycaster-tia-vblank.json` validates eight 128-byte
VBlank-only transfers including the page boundary. A generic raster plan
still rejects uninterruptible blocks longer than 16 bytes during active
display. A passing offline budget is not a proven hardware VBlank deadline.

When profiling LLVM-MOS SDK block moves, note that `pce_memop` has a
single-byte `.mlb` symbol. `cycle_profile.py` uses only the explicit
`.pce.map` section length to label that routine; the emulator still charges
some TIA transfer time to synthetic non-ROM PC values. Budget those as
**unmapped ticks** rather than inventing a performance win or hiding them.


### Paired-BAT bitmap modes (PCEdev's Wolf3D articles)

For any raycaster/Mode 7 request, distinguish physical 512x224 display from
128x128 or 128x64 *logical* pseudo-bitmap pixels. A full 128x128 image fills
all 8192 BAT words and cannot be full-resolution double-buffered inside that
BAT. The `34-rendered-raycaster` default is full-detail progressive; its
`make atomic-rom` variant uses two 4096-word BAT halves at 128x64 and swaps
only at VBlank. Do not silently substitute the atomic mode as a 128x128
speedup; verify with `make atomic-test`, and state the loss of vertical detail.
Use `pce-development/workflows/paired_bat_plan.py` for layout verification.
PCEdev's speculative palette/dither expansions are NOT working implemented
32- or 256-colour bitmap modes in this toolkit.

## Raycaster full-detail shader performance gate

For `34-rendered-raycaster`, keep the default 128x128 full-detail BAT mapping.
The old double `wall_pixel()` call per BAT entry has been replaced with a
**generated, exact, two-texel table** (`tools/gen_wall_pairs.py`). Select
`wall_style` only when casting the 32 rays, then look up `ray_wall_pairs` per
visible wall pair. Never hand-edit the generated header or add target-side
multiplication/index strides; run `make tables-check` and
`make wall-lookup-check` first. A compiler/link success alone is insufficient:
run `make wall-lookup-visual` for exact 600-frame emulator pixel agreement,
`make wall-lookup-throughput` for equal-resolution completed-BAT counters,
`make interaction-test` for collision, and `make cycles-ray` for mapped ROM
master-clock regression limits. Do not claim function-local cycle changes
when inlining moved the shader into `main`.

Keep the 128x64 atomic BXR-flip renderer as a **different binary** with
`make atomic-test`. Its half-height frame swaps are not directly comparable
to 128x128 complete passes. Mirroring top/bottom would require an intentional
symmetric scene and different raster mapping; do not claim it happens here.

## Fast raycaster: do not regress to a CPU framebuffer

For `examples/34-rendered-raycaster`, the full-detail default uses a 32 KiB
HuCard ROM with offline-generated BAT backdrop, VDC +128 vertical address
increments, short 16-byte IRQ-bounded `TIA` bursts and a 127-event native
raster IRQ. Do not convert it back to full-sky/floor pixel loops or a RAM
framebuffer. Always run `make tables-check`, `make column-regression`,
`make column-benchmark`, `make visual-test`, and `make interaction-test` before
claiming an FPS improvement. A dirty-column presentation is NOT equal pixel
work to an old 128x128 complete repaint: report changed views, uploaded BAT
words and input scenario separately. `atomic-rom` is a different 128x64
half-page renderer, and must never silently replace the full-detail build.
PCEdev's 15-30fps discussion is a design estimate, not performance evidence
for this example. The fast background stays screen-anchored while walls move;
implementing perspective floor motion is future work, not an achieved feature.

## Generated wall-code raycaster (example 34)

Do not claim fast Wolfenstein frame rates from screenshot appearance. The
full-detail 128x128 raycaster now uses `tools/gen_wall_codegen.py` to generate
fixed-offset HuC6280 wall writers, with 8-word IRQ-bounded vertical VRAM
bursts. Use `make tables-check`, `make codegen-benchmark`, and
`make column-regression`; the benchmark requires both real emulator image
agreement and ROM-owned codegen word counters. Keep `make atomic-test`
separate: it builds the independent 128x64 page-flipped mode, which has
lower vertical detail. The C reference ROM remains `make codegen-reference`.

- For Wolf textures, preserve the original 7x32x32 atlases in example 34's assets. Run `make raycaster-texture-sheets` and rebuild the packed paired-pixel table before claiming a texture change works.
- Different C vs assembly page-switch screenshots can disagree on precisely one physical row; report it quantitatively. Never claim pixel-perfect equality when the comparison says `matched: false`.
- SGX two-VDC plane conversion is currently offline-only; do not tell users it is a running 256-colour SGX ROM without a VPC-composited emulator capture.

### Full-detail raycaster scalar-span acceptance

Use `PCE_HEADLESS=/path/to/rpc-capable/pce-headless make raycaster-scalar-fps`
when optimizing short wall tails. Build **same-art, same-128×128** ROMs with
`RAY_COLUMN_TIA=1` (reference) and bounded direct VDC writes (optimized).
The tool checks real input-driven emulator views, VRAM-word counters and a
600-frame stationary screenshot comparison. Never compare the separate 128×64
atomic presentation mode as though it renders an equal number of pixels.
Changing the controller scenario or texture source invalidates the speed
comparison. Keep the generator-built aligned eight-row assembly writer, and
never extend the active-display IRQ mask beyond eight BAT words/16 bytes.
