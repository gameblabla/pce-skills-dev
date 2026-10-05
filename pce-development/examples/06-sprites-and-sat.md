# Example 06: sprites, SAT, and admission

**Build contract:** A project created or changed from this recipe copies the [starter Makefile](starter/Makefile) and all files under [`starter/tools/`](starter/tools/), includes `tools/llvm-mos-sdk.mk`, and makes each compile, assemble, and link target depend on `toolchain`. CD boot targets also run `bios-check`.

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
