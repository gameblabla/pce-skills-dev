# Example 29 — Static picture + protagonist mouth sprite (visual novel)

A real, buildable 32 KiB HuCard scene with **no sound**. A coherent pixel-art observation room, protagonist, and dialogue panel are one 256×224 static background. The protagonist's mouth is **not repainted into the background**; it is a separate 16×16 hardware sprite with closed and open patterns and an independent sprite palette. The static picture stays resident, and the SAT sprite pattern index switches about every twelve VBlanks. The demo changes only 43 pixels in the mouth region.

The source art lives in `assets/background.png`, `assets/mouth_closed.png` and `assets/mouth_open.png`. The generated C, palette, BAT, and patterns are in `src/vn_assets.{c,h}`, produced by `tools/vn_pack.py`. The generated file is checked by `model_guard.py` against its source PNG hashes and output SHA-256; no exception is granted to hand-written enormous C arrays. The graphics tool is **Pillow-only in single-palette mode** and works entirely offline.

```
make assets             # validate PNG sizes, deduplicate BG tiles, generate C, preview and VRAM manifest
make                    # compile HuCard with LLVM-MOS
make run                # neutral-input emulator screenshot
make trace              # G2TR v2 visual-novel scene, portrait, mouth and dialogue state
make visual-test        # two actual emulator captures (closed/open), assert ONLY mouth pixels change
make model-check        # test regeneration of assets (no compiler, no network)
```

`make assets-multi` opts into 16 tile-local **background** palettes via the bundled `picture.py`/`palfit.py` fitter (Pillow + NumPy). The default 1×16 BG palette is more portable and keeps the starter small; multi mode offers up to 16×16 background palette entries and can increase or decrease the number of unique patterns. Sprites have a **separate** 16-colour sprite palette, with index 0 reserved for transparency. Both modes check VRAM regions: BAT `$0000–$03ff`, patterns from `$0800`, sprite patterns `$6000`, and SAT `$7f00`. Do not confuse these VDC word addresses with byte offsets, sprite pattern indices, or emulator screenshot dimensions.

The tool refuses a background other than 256×224, a mouth frame other than 16×16, a mouth sprite exceeding 15 opaque colours, more than 512 unique background patterns, or overlapping VRAM allocations. Manifest reports pattern deduplication, changed pixels, palette use, input hashes, and exact VRAM ranges. `tools/vn_visual_check.py` independently checks the actual emulator snapshots; `tools/genre_trace.py` validates the game-authored G2TR records.

To generate a new original teaching picture and mouth frames without external image services:

```
python3 tools/vn_pack.py demo --out assets
```

**Scope:** one original dialogue frame, an animated protagonist mouth, and a verifiable asset/runtime pipeline. It is not a complete dialogue scripting engine, branching visual novel, CD/ADPCM movie player, or proof of physical console timing. For full-colour photographic/title screens, see example 16's original `picture.py` multi-palette converter; for other genres use `tools/pce/GENRE_TRACE.md`.
