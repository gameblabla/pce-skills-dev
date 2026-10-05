# Visual debugging with images and source code

Use this guide when a request describes appearance rather than a symbol or
line of code: “the HUD is too low,” “the ship should be centered,” or “that
panel covers the player.” Combine the provided image with active source,
generated assets, mode, and runtime display state.

## Trace a visual request

1. Identify which game/scene/mode and which visible element the user means.
   Verify the image comes from the current build, if possible.
2. Inspect element bounds, alignment, margins, and overlap at native
   resolution. Use Python or an image tool if a pixel measurement matters.
3. Find its drawing code and generated asset/manifest entry. Determine whether
   coordinates are screen-space, world-space, camera-relative, BAT/tile space,
   or VDC dots/words.
4. Follow transformations in order: source state -> camera/scroll -> display
   mode/scaling -> SAT/BAT submission -> frame-boundary publication -> image.
5. Make the smallest coherent change to the intended visual group. Preserve
   spacing, clipping, alignment, and safe-edge margin. Keep fixed HUDs in
   screen-space; do not move world simulation coordinates to fix a HUD.
6. Rebuild and capture the same scene/state/frame. Confirm the intended visual
   moved, unrelated actors/background stayed fixed, and no new overlap or
   clipping appeared.

If image and source disagree, verify build identity and asset generation before
changing code. If multiple UI groups could match the instruction, trace the
candidates and ask one concise clarification only when ambiguity remains.

## Multimodal local AI

Send the screenshot/video frame and relevant source snippet in one request when
the local endpoint supports image input. The eval runner supports case-level
image fixtures using OpenAI-compatible `image_url` message content. If the
endpoint rejects images or is text-only, state that the image was not inspected.

For video, compare matching frame indices around the event. Use Python for
pixel bounds, displacement, crop, color, timing, and exact coordinate-offset
calculations. If no measurement/tool output exists, keep the suggested visual
adjustment qualitative. Visual
similarity does not prove collision, input, bank mapping, or physical timing.

See [`examples/11-visual-request.md`](../examples/11-visual-request.md) for a
self-contained vague-HUD request and expected reasoning.
