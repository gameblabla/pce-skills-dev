# Example 11: “The HUD is too low; move it higher”

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/11-visual-request.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

This example is self-contained and does not require any game's source tree.
Assume the user provides a screenshot and the current project includes this
source evidence:

```c
/* Fixed screen-space HUD elements: x, y, sprite id. */
static const HudItem hud[] = {
    { 12, 18, HUD_LIVES },
    { 48, 18, HUD_HEALTH },
    { 12, 38, HUD_WEAPON },
};

/* World actors use a camera transform; HUD items do not. */
screen_x = world_x - camera_x;
screen_y = world_y - camera_y;
```

## Reason from both modalities

1. Inspect the image and identify which HUD row the user means. Check top/side
   margins, spacing between icons, relationship to the playfield, and whether
   the screenshot belongs to the active build/mode.
2. Trace the source code: the HUD uses fixed screen coordinates while actors
   are transformed by the camera. The HUD must not receive actor camera math.
3. Select a small upward adjustment after reviewing the screenshot at native
   resolution. Use `scripts/calc.py` or Python image measurement for any exact
   pixel offset or coordinate conversion. Keep all HUD items in the intended
   group aligned and preserve their relative spacing. If no measurement is
   available, recommend the direction only and do not invent an exact or
   approximate pixel range. Do not infer spacing or bounds by subtracting
   coordinates in prose. Without Python tool output, do not write new numeric
   coordinates or an example pixel delta.
4. Rebuild and capture the same scene. Confirm that the HUD moved upward,
   actors and background stayed fixed, and no icon clipped or covered another
   element.
5. Add an assertion for the HUD's screen-space anchor and a visual comparison
   for the same state. If camera movement/shake exists, verify the HUD remains
   fixed while actors move.

Do not start by moving the camera or all world objects. If the image and source
do not identify which HUD group is meant, trace candidate groups and ask one
specific question only if ambiguity remains.

## Endpoint requirement

The local model must receive both the image and this relevant source snippet.
If its inference API is text-only, say that the visual part could not be
inspected and do not claim otherwise. The skill's eval suite includes a
portable image fixture and source snippet to check that image-aware workflow.


## Included visual fixture

Use [`assets/hud-too-low.png`](assets/hud-too-low.png) with its editable [`assets/hud-too-low.svg`](assets/hud-too-low.svg) alongside the source snippet and `src/main.c`.
