# Example 06: sprites, SAT, and admission

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/06-sprites-and-sat.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

## Asset and renderer records

Bake each sprite to target pattern data plus a semantic manifest entry
containing pattern start, palette, dimensions, anchor/hotspot, and animation
frames. The runtime renderer should translate world/screen coordinates, check
SAT and scanline budgets, assign pattern slots, and queue SAT changes for a
coherent frame publication.

Keep gameplay state separate from draw admission. A sprite refused because a
scanline or SAT is full may be hidden for a frame, but a refused optional shot
must not still collide. Prefer to reject a projectile spawn when it cannot be
drawn; if an active projectile is refused, cancel/freeze it and suppress its
collision for that frame. Use refusal pressure to throttle later optional
shots/effects until capacity recovers. Essential player, boss, and hazard
sprites should have explicit priority over particles and cosmetic effects.

## Draw plan

```text
begin_frame():
    clear_next_sat_and_scanline_usage()
    enqueue_essential_player_and_hazards()
    enqueue_required_gameplay_projectiles()
    enqueue_optional_effects_and_background_actors()
    for each queued item in priority order:
        if sprite_fits_all_hardware_budgets(item):
            reserve_sat_entry_and_scanlines(item)
            ensure_patterns_resident(item.patterns)
            write_sat_entry(item)
        else:
            record_refusal(item)
            apply_projectile_gameplay_policy(item)
    publish_sat_and_matching_scroll_at_frame_boundary()
```

The loops are pseudocode; use the project's target types and real SAT format.
Never rely on a `no sprite limit` emulator option to make a test pass.

## Test matrix

Test zero actors, one player, one overlapping pair, full SAT, scanline width
pressure, mirrored/flipped patterns, clipped screen edges, optional shot
refusal, and transition from crowded to empty. Assert both visible admission
and gameplay outcome. A passing empty scene does not exercise the full-budget
path.


## Included sprite source

[`assets/sprite-sheet.svg`](assets/sprite-sheet.svg) and its PNG are the editable fixed-cell sheet fixture. Run `make convert-assets` to bake it into shared-palette sprite patterns, frame records, preview, and manifest under `build/sprite-sheet/`. `assets/demo_assets.h` contains the compact target pattern used by `src/main.c`.
