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
