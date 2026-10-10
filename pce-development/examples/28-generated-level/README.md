# 28 — Deterministic offline-generated level / 4bpp tilemap

**Category: graphics.** One source `assets/level.json` describes tiles, 64x28 map, collision glyphs, and spawn/enemies/goal **in tile coordinates**. `tools/assetpack.py` validates row widths and pixel values, encodes PCE 4bpp planar 8x8 patterns (32 bytes per tile), emits one C translation unit and declarations, and provides size estimates. Its outputs are generated in `build/`, not hand edited.

`make assets-check` validates without a compiler; `make` regenerates assets when JSON changes, builds a HuCard; `make run` runs via the headless wrapper. The rendering ROM intentionally demonstrates the generated **background only**: enemies, flag collision, player physics and title/death states are level *metadata* requiring a game engine, not gameplay implemented by this ROM. See example 26 for the P2TR platformer engine.

No sound, text or controller library is initialized. This is a **32x28 visible tile** window over a 64x28 world. The project is self-contained after copying to another folder. Tile counts are bounded to avoid linker overflow; for larger maps, use chunked banks/streaming instead of silently shortening the level.
