# Example 08: 2D platformer

**Project:** Run `make` in this folder to compile `src/*.c` and `src/*.S` to `build/08-platformer.elf` with the bundled LLVM-MOS setup. `make bios-check` checks local CD System Card setup. The ELF is not a packaged CD image; IPL and disc layout remain project-specific.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable visual fixture. See additional files in this folder for topic-specific data.

Keep world position, camera position, and screen position separate. A useful
runtime split is input/state update, collision-map query, actor/projectile
simulation, camera, background stream, sprite admission, and frame publication.
Store large maps and collision columns in Arcade RAM; keep only the working
column/cache and active actor state in CPU-accessible memory.

## Frame path

```text
tick(input):
    apply_input_to_player_state(input)
    integrate_velocity_and_fixed_point_remainder()
    resolve_horizontal_collision_against_map()
    resolve_vertical_collision_against_map()
    update_enemies_and_projectiles()
    advance_camera_without_moving_world_state()

draw_frame():
    stream_required_map_columns_into_unreferenced_cache_slots()
    compose_next_background_and_sat_generation()
    publish_matching_scroll_and_sprite_state_at_vblank()
```

Pseudocode only. Define units, signs, fixed-point scale, coordinate origin,
and rounding rules in named project types. Use Python for conversions and
boundary calculations; do not make the model mentally multiply fixed-point
values.

## Collision and cache rules

- Query every map cell touched by the actor's leading/trailing edges.
- Preserve fractional movement when an integer pixel does not advance.
- Keep collision-map streaming independent from visible tile cache lifetime.
- Hold outgoing visible pattern slots through the VBlank that removes them.
- Prevent a rejected optional projectile from causing invisible damage.

## Tests

Exercise flat ground, each platform edge, ceiling, wall, one-way/drop-through
surface, fall/respawn, scroll boundary, cached-column replacement, crowded
sprites, and a camera-stationary HUD. Check both map collision and the matching
rendered frame. Include minimum/maximum velocities and world positions using
the calculator helper.
