# Skills for Local AI PC Engine Development

Use this with opencode or similar to start writing your 
own PC engine game or application for Hucard or (Super/Arcade) CDROM² !

I recommend that you get the strongest local AI model that you can possibly
use for your PC.
## Single-purpose C examples

The 99 small examples are in [`pce-development/examples/micro/`](pce-development/examples/micro/README.md).
Each ROM has one `main.c` and shared compiler rules. Sound examples produce
sound without video initialization, and debugger examples expose volatile
state instead of displaying unrelated text or graphics. The full historical
recipes remain in `pce-development/examples/`, with nine non-visual lessons
now isolated from video helpers.

Bitmap/old Mode 7 floor lessons: [`85-bitmap-128-circle`](pce-development/examples/micro/85-bitmap-128-circle/) and [`86-mode7-bitmap-floor`](pce-development/examples/micro/86-mode7-bitmap-floor/). Both use the 512×224 paired-BAT pseudo-bitmap trick; the [historical implementation notes](pce-development/examples/micro/BITMAP_MODE7_HISTORY.md) link to the pre-replacement Saber Rider sources.

## Local AI bring-up and actual game starters

A deterministic workflow router is in [`pce-development/workflows/`](pce-development/workflows/README.md). It selects a suitable *runnable* recipe rather than prompting a weaker coding model to synthesize hardware details. It includes JSON game-rule validation/generation, offline X/Y/gravity/scene simulation, no-overwrite scaffolding, ROM and image audits, native-ROM scene probes for a newer headless frontend, and unit tests. None of these require network/API access. Raw transcripts are not distributed.

Use `make help` and `make test` at repository root. Runnable full-project starters are [`26-platformer-starter`](pce-development/examples/26-platformer-starter/README.md) and [`27-platformer-racer`](pce-development/examples/27-platformer-racer/README.md). The 512×224 paired-BAT Mode 7 lesson remains a separate renderer recipe and is **not** quietly replaced by the phase-transition demo's road art.

### Hardening from further local-AI failure transcripts

See [local-model failure fixes](pce-development/references/local-ai-transcript-fixes.md). The new `model_guard.py` catches hallucinated SDK names, relays actionable compile/ROM overflow and headless RPC diagnostics, and gates unverified gameplay/CD claims. `assetpack.py` generates safe 4bpp planar tiles and BAT maps from JSON, with a new standalone **example 28**. Root `make agent-check agent-assets agent-build` runs the related checks and build. Original private transcripts are not included.

### Genre-neutral trace and visual-novel pipeline

Legacy platformer **P2TR v1 stays supported**. New **G2TR v2** instruments shmup, raycaster, racing, platformer (coarse) and visual-novel game state without inventing platform-collision semantics for other genres. From the repo root: `make genre-check` (offline), `make genre-build` (LLVM-MOS) or `PCE_HEADLESS=... make genre-test` (actual emulator). See `pce-development/tools/pce/GENRE_TRACE.md`.

Example 29 is a real static-scene visual-novel ROM with a separate 16×16 animated mouth sprite, preview and VRAM/palette audits; `make assets` converts original PNGs while `make visual-test` compares two actual emulator captures. Example probes 30–32 exercise nonvisual genre-specific trace publication. See `pce-development/examples/29-visual-novel/README.md` and the offline routing tool's `visual_novel`, `shmup_trace`, `raycaster` and `racing_trace` recipes.

### Rendered cross-genre acceptance examples (new)

Examples [33-rendered-shmup](pce-development/examples/33-rendered-shmup/),
[34-rendered-raycaster](pce-development/examples/34-rendered-raycaster/) and
[35-rendered-racer](pce-development/examples/35-rendered-racer/) add actual
BG/SAT or raycast-BAT graphics and controller response **without replacing**
nonvisual G2TR probes 30–32. `make visual-games-build` builds all three and
`PCE_HEADLESS=... make visual-games-test` runs independent input-driven G2TR
and PNG-difference checks. Screenshots are compared *inside gameplay regions*,
not just checked for existence.

`pce-development/tools/pce/scene_pack.py` converts tightly specified 256×224
RGB scenes and four 16×16 transparent sprite frames (64×16 atlas) into
palette-safe, deduplicated PCE tiles, BAT, and sprite data, with manifest and
VRAM overlap checks. `visual_scenario.py` couples scripted input, framebuffer
captures, trace input latching, and movement/diff thresholds. These tools and
assets are bundled inside the standalone example projects. The raycaster is
an actual 32-ray renderer writing two independent four-bit pixels per BAT
entry, *not* a static image or 8px solid-colour BAT columns. Run
`PCE_HEADLESS=... make raycaster-bitmap-test` for its independent 512×224
bitmap screenshot audit. Game traces remain separate from visual evidence.

These teaching ROMs are not fully featured commercial games; the raycaster has
textured stone/brick/metal walls through the 512×224 paired-BAT bitmap backend, and the racer
uses a fixed perspective background rather than the separate paired-BAT Mode 7
engine. The screenshot checks prove rendered changes in an emulator, not sound,
collision completeness, performance guarantees, or physical hardware timing.


### Verified gameplay interactions and offline SAT planning

Rendered examples 33–35 now contain reproducible **gameplay rules**, not just
movement: player shots destroy shmup enemies, hostile shots inflict damage,
raycaster movement blocks on mapped walls, and the racer has checkpoints,
laps and traffic contact with a speed penalty. `make interaction-test` drives
these events on an actual RPC-capable emulator and saves per-tick G2TR data;
`make interaction-replay` reruns the corresponding assertions offline. The
shmup also runs a combat screenshot test with independent pixel-region changes
and G2TR counter deltas. The
old `make visual-games-test` remains independent screenshot evidence.

`make sat-check` tests offline SAT priority/admission planning. Use
[`sat_budget.py`](pce-development/workflows/sat_budget.py) before expanding
sprite-heavy code and see
[`interaction-and-sat-verification.md`](pce-development/references/interaction-and-sat-verification.md)
for event names, map checks, budget limits and the evidence ladder.

## No implicit software arithmetic on HuC6280

Run `make arith-check` offline before compiling new ROM code. Newly authored
CPU sources must use 8/16-bit integer values, not 32/64-bit integers or
floating-point operations; do not link GCC `-lgcc` or `-lm`. Existing frozen
P2TR/G2TR wire layouts, legacy game math and hardware address code are
**46 audited compatibility exceptions** tracked by exact line fingerprints in
`pce-development/workflows/specs/arith-legacy.json`; these remain migration
work, not an all-project-wide elimination of wide integers.

Use `pce-development/libcommon` for shift/add narrow math and offline Mode7
lookups. `make arith-build` compiles/link-audits the BAT circle, Mode7 road and
four new arithmetic micro demos, refusing `__mul*`, `__div*`, `__mod*` or
`libm` symbols in those ELF files. The checker is based on actual ELF symbols;
LLVM-MOS software integer helpers are *not* GCC libm functions.

### Frame-transfer budgets and arithmetic on HuC6280

Before adding a scrolling scene, run `make vram-check`. The sample
`pce-development/workflows/specs/vram-streaming.json` describes a layout in
**VRAM words** and transfers in **bytes**, models BAT front/back pages and an
SAT shadow, and checks the upload queue against *explicitly supplied* per-frame
byte and IRQ-block budgets. `vram_budget.py` refuses overlaps, visible BAT
writes without a declared VBlank restriction, and block moves longer than 16
bytes with raster interrupts enabled. It also works with two separate
SuperGrafx VDCs. `scene_vram.py examples/33-rendered-shmup` and the matching
racer command check **actual generated** `scene_assets.h` array sizes against
`scene_manifest.json` VRAM allocations, rejecting overlapping or stale assets. The byte budget is an **assumption**, not a measured VBlank
cycle count; follow it with G2TR and emulator screenshot acceptance tests.

`make arith-games` now link-audits the three graphical shmup/raycaster/racer
starters as well as `make arith-audit-all` covering all micro ROMs. The
raycaster's 32 rays use generated 8-bit signed sample steps plus wall-height
lookup tables (`34-rendered-raycaster/tools/gen_ray_tables.py`), removing
runtime generic multiplication/division. The racer uses small modular phase
accumulators for traffic scroll positions and a shift for checkpoints.
`make performance-check` validates the generated tables and VRAM budget
without fetching a compiler. These are deterministic *functional* speedups:
actual frame times or CPU-cycle improvements have **not** been measured.

The original P2TR world-coordinate code and G2TR wire ABI still contain
frozen, reviewed 32-bit compatibility exceptions. Do not copy those wide
integer types into new gameplay. This toolkit's strict ELF math gate now
covers the three rendered genre starters; the two legacy platformer demos
still need an isolated narrow-physics migration.

## Platformer performance rewrite: 16-bit Q4 and compact P4TR v4

Examples 26 and 27 now use **signed 16-bit Q4** movement and camera values
instead of 32-bit Q8 physics. Both use two 32-byte P4TR records (64 bytes
combined), with platform geometry audited independently from
`assets/platform_layout.h`. There is no dependency on P2TR's special
`trace_frames` emulator command. `make arith-games` checks the linked binaries
for software multiplications and divisions.

`make platformer-check` runs host-only differential and malicious-trace tests;
`PCE_HEADLESS=... make platformer-test` runs scripted ROM movement and a
598-frame hybrid platformer/racer/platformer round trip, **followed by another
20 frames of movement** to prove the game does not freeze after returning. The
SAT update in example 27 is four VDC word writes, not a blocking SDK SAT copy.
The older P2TR examples are historical references, not the default for new AI
projects. See `pce-development/references/q4-platformer-and-p4tr.md`.

For a reproducible instruction-count comparison against a local older checkout:

```sh
PCE_BASELINE_ROOT=/path/to/ca35950-checkout PCE_HEADLESS=/path/to/pce-headless make platformer-perf
```

The report is `build/platformer-perf/comparison.json`. It compares compiled
BSS, linked compiler helper symbols, unique executed PC addresses and emulator
instruction counts across 240 equal-length idle-input frames. These are **not
CPU-cycle measurements**, and the busy-wait work limits speed conclusions.

## CPU cycle attribution (not only instruction counts)

The bundled Mednafen-derived headless emulator has `prof_start` and `prof_dump`
RPC commands. `pce-development/workflows/cycle_profile.py` maps their **physical
HuC6280 master-clock counts** to the linked ROM's `PcePrgRom` addresses in
LLVM-MOS's `.mlb`. It does not mistake logical `$E000` for a physical ROM
address or classify VBlank wait cycles as game logic. It reports functions,
interrupts, software helpers, unknown physical addresses and game-state
progress, using the same scripted inputs in each run.

```sh
PCE_HEADLESS=/absolute/path/to/pce-headless make cycles-ray
PCE_HEADLESS=/absolute/path/to/pce-headless make cycles-all
make cycles-check # completely offline; no compiler/emulator download
```

See `pce-development/workflows/CYCLE_PROFILING.md` for method, actual emulator
results, measurement caveats, per-routine budgets and regression instructions.
**These are cycle costs in the emulator, not physical-hardware benchmarks or
host CPU wall time.** Real screenshot and input trace validation remain required.

### Faster native bitmap raster IRQ

The 512x224 paired-BAT **Mode 7** and raycaster originally shared a
register-preserving native HuC6280 raster IRQ from `libcommon/src/bat_bitmap_irq.S`.
Mode 7 still schedules 223 physical scanline events; the **fast full-detail
raycaster** instead uses its own `src/bat_sparse_irq.S` for 127 logical-row
transitions, while its atomic/reference variants retain the previous handler.
The original native IRQ change made register updates much cheaper:
about half the emulated raster-IRQ master ticks in Mode 7 and 59–60% fewer
in the earlier raycaster; the later sparse variant reduces its IRQ cost again.
The full ROM symbol range is accounted for. The raycaster
also advances more game updates under matched controller inputs; update
counts differ from baseline, so this is *not* a same-work timing comparison.
Use `make cycles-ray`, `make raycaster-bitmap-test`,
`make raycaster-throughput`, and `make test` before claiming a performance improvement. See
[`CYCLE_PROFILING.md`](pce-development/workflows/CYCLE_PROFILING.md).

### Fast, vertically streamed full-detail raycaster

Example 34 now follows PCEdev's **VRAM-resident bitmap** approach instead of
redrawing the entire pseudo-framebuffer in C. It initializes a generated 16 KiB
sky/floor BAT backdrop once, casts real map rays on camera changes, and writes
only changed textured wall spans using the VDC's **128-word vertical stride**.
Short 16-byte TIA bursts are independently interruptible. A generated sparse
raster IRQ handles 127 logical row transitions instead of 223 physical lines.
The full-detail 128×128 renderer remains separate from the opt-in 128×64
atomic page-flip version.

The faster ROM uses 32 KiB instead of 8 KiB HuCard space, while its BSS
falls from 1,331 to 487 bytes. **Changed views** and actual BAT words written
are counted separately; they are not falsely equated with the old full-frame
redraws. The ROM still falls short of the PCEdev blog's projected 15–30 FPS,
and its fixed decorative floor does not scroll with the camera. See the
[project README](pce-development/examples/34-rendered-raycaster/README.md) for
measured emulated update rates, limitations and commands. Use:
`PCE_HEADLESS=... make raycaster-throughput` or in the project
`make column-regression column-benchmark`.


### Historical 640-byte wall-pair lookup (now used by column streaming)

The 128x128 full-detail raycaster retains the offline-generated 640-byte
pre-shaded wall-pair lookup from
`examples/34-rendered-raycaster/tools/gen_wall_pairs.py`. In the **previous**
full-image row renderer, this yielded 19 complete BAT passes instead of 16
per 1,080 video frames, with bit-identical stationary screenshots. That
historical same-renderer comparison is **not** a speedup ratio for the new
VRAM-resident dirty-column path. `make raycaster-wall-lookup` now runs the new
column benchmark and explicitly distinguishes dirty wall updates from complete
background-and-wall redraws; `make wall-lookup-visual` separately checks that
one settled screenshot still matches the old shader pixel for pixel.

The 128x64 atomic BAT-half-page mode remains optional, separately compiled
and tested (`make raycaster-atomic`). Mirrored scenes may be a useful future
application; they are not part of the current example.

### Pre-generated HuC6280 raycaster vertical wall writers

`PCE_HEADLESS=/path/to/RPC-emulator make raycaster-codegen` builds the
same-resolution C/TIA and generated-assembly 128×128 raycaster variants,
compares rendered pixels exactly, and measures actual ROM-authored dirty
views and generated-code BAT words. The eight-row unrolled paths are
interrupt-bounded and keep the separate 128×64 atomic renderer unchanged.
See `pce-development/examples/34-rendered-raycaster/README.md` for tradeoffs.

### Source texture atlases and measured raycaster writers

The full-detail raycaster now ships with the supplied 16-colour Wolf texture
atlas, offline generation of 14 material/shade paired-pixel classes, and a
losslessly compressed 14-row backdrop. `make raycaster-texture-sheets` verifies
the texture and SGX dual-plane *asset plan* offline; the SGX compositor itself
is not implemented. The full-resolution assembly-vs-C/TIA benchmark is
`make raycaster-codegen`. The atomic 128x64 renderer remains independent.
