# Example 07: large animation by staged pattern swaps

**Build contract:** A project created or changed from this recipe copies the [starter Makefile](starter/Makefile) and all files under [`starter/tools/`](starter/tools/), includes `tools/llvm-mos-sdk.mk`, and makes each compile, assemble, and link target depend on `toolchain`. CD boot targets also run `bios-check`.

When an animation contains more graphics than can remain resident in VRAM,
store frame data or deltas in Arcade RAM and upload only the required patterns.
Do not overwrite patterns still named by the displayed SAT or BAT.

## Offline representation choices

- **Shared base plus deltas:** each frame lists changed pattern IDs and bytes.
- **Pose sets:** each pose is a descriptor for a bounded group of patterns;
  common pieces are shared.
- **Streaming chunks:** a frame is loaded over several video intervals while
  a hold, fade, or other intentional presentation covers incomplete pieces.

The asset builder should validate every frame descriptor, source extent,
destination VRAM allocation, palette, and worst-case upload budget. Use Python
for the total byte and frame-budget calculations.

## Safe swap timeline

```text
prepare_frame(next):
    identify_patterns_not_used_by_currently_displayed_generation()
    stage_next_pattern_bytes_in_arcade_ram()
    upload_to_unreferenced_vram_slots_in_bounded_chunks()
    verify_all_upload_chunks_completed()
    at_vblank:
        build_sat_or_bat_references_for_next_generation()
        publish_new_references_and_scroll_together()
    after_old_generation_is_no_longer_visible:
        release_old_pattern_slots()
```

If a full frame cannot fit in one safe update window, split it across frames
or reduce data. Keep raster/audio IRQs serviceable between bounded chunks; do
not mask interrupts across the full-frame copy. Only use a short critical
section for per-chunk VDC address/index updates when required. Don't free cache
slots as soon as the CPU starts filling the next frame; the old generation can
remain visible until VBlank.

## Regression

Capture the first pose, an interior pose, the last pose, wrap/reverse behavior,
and a scene transition. Assert descriptor identity, upload completion, no
reference to an uninitialized slot, and visible output in matched frames. Test
under simultaneous sound/raster work if those share the CPU/Arcade Card path.
