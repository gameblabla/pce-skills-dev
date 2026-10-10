# Skills for Local AI PC Engine Development

Use this with opencode or similar to start writing your 
own PC engine game or application for Hucard or (Super/Arcade) CDROM² !

I recommend that you get the strongest local AI model that you can possibly
use for your PC.
## Single-purpose C examples

The 85 small examples are in [`pce-development/examples/micro/`](pce-development/examples/micro/README.md).
Each ROM has one `main.c` and shared compiler rules. Sound examples produce
sound without video initialization, and debugger examples expose volatile
state instead of displaying unrelated text or graphics. The full historical
recipes remain in `pce-development/examples/`, with nine non-visual lessons
now isolated from video helpers.
