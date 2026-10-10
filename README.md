# Skills for Local AI PC Engine Development

Use this with opencode or similar to start writing your 
own PC engine game or application for Hucard or (Super/Arcade) CDROM² !

I recommend that you get the strongest local AI model that you can possibly
use for your PC.
## Single-purpose C examples

The 95 small examples are in [`pce-development/examples/micro/`](pce-development/examples/micro/README.md).
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
an actual coarse 32-column ray stepper, *not* a static image labelled raycast.

These teaching ROMs are not fully featured commercial games; the raycaster has
solid-colour distance-shaded walls rather than textured walls, and the racer
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
