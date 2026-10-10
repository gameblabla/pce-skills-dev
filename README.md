# Skills for Local AI PC Engine Development

Use this with opencode or similar to start writing your 
own PC engine game or application for Hucard or (Super/Arcade) CDROM² !

I recommend that you get the strongest local AI model that you can possibly
use for your PC.
## Single-purpose C examples

The 87 small examples are in [`pce-development/examples/micro/`](pce-development/examples/micro/README.md).
Each ROM has one `main.c` and shared compiler rules. Sound examples produce
sound without video initialization, and debugger examples expose volatile
state instead of displaying unrelated text or graphics. The full historical
recipes remain in `pce-development/examples/`, with nine non-visual lessons
now isolated from video helpers.

Bitmap/old Mode 7 floor lessons: [`85-bitmap-128-circle`](pce-development/examples/micro/85-bitmap-128-circle/) and [`86-mode7-bitmap-floor`](pce-development/examples/micro/86-mode7-bitmap-floor/). Both use the 512×224 paired-BAT pseudo-bitmap trick; the [historical implementation notes](pce-development/examples/micro/BITMAP_MODE7_HISTORY.md) link to the pre-replacement Saber Rider sources.
