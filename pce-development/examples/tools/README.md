# Example graphics tools

Run these scripts with Python 3 from any working directory. Paths are resolved
relative to the scripts, so no sibling game project or BIOS is needed.

`generate_graphics.py` requires Pillow and NumPy. Edit its `scene()` and
`sprites()` functions to change the original pixel artwork. It writes each
numbered project's indexed `assets/source.png`, `assets/sprite-sheet.png`, and
embedded `assets/demo_assets.h`. Pixel colors are selected directly from the
9-bit hardware palette; background characters are deduplicated and packed
with the shared PCE format encoders. The BAT describes a periodic world wider
than the small viewports. The source PNG shows the initial visible crop, while
the embedded BAT retains the complete map for scrolling.

```sh
python3 generate_graphics.py --example 8
```

`capture_screenshots.py` builds the selected projects with their local
Makefiles, explicitly releases all controller buttons through the emulator's
RPC input command, runs the requested frames, and replaces each
`assets/screenshot.png` only after a successful capture. It uses a fresh
emulator configuration directory for every project. The bundled headless
binary must first be built using the headless source snapshot's
`README_HEADLESS.md` build instructions.

```sh
python3 capture_screenshots.py --example 8
python3 capture_screenshots.py --emulator /path/to/pce-headless --frames 120
```

Platformer examples also include `tools/platformer-trace.py`. Copy it with the
starter Makefile and tools, add a P2TR v1 state record to the game, then call
`make trace PCE_PLATFORM_TRACE_ADDRESS=... PCE_PLATFORM_TRACE_SCENARIO=...`.
The helper applies scripted controller input and returns a concise text report
from per-frame game state. Read
[`../../references/platformer-rules.md`](../../references/platformer-rules.md)
for the ABI and interpretation limits.

Generated backgrounds, sprite patterns, and the font occupy separate VRAM
regions. SAT pattern fields use 32-word address units, so the pattern at VRAM
word 0x6000 is named by SAT value 0x0300. Each sprite is placed in front of the
background. The renderer clears all SAT entries and enables automatic SAT
transfer at VBlank before drawing sprites.
