# Example 19: enemies, projectiles, and hit rules

![Example 19: enemies, projectiles, and hit rules emulator screenshot](assets/screenshot.png)

**Project:** Run `make` in this folder to build `build/19-enemies-and-shooting.pce` with the bundled LLVM-MOS setup. This HuCard ROM can run in a PC Engine emulator. CD-ROM² deployment needs project-specific IPL/disc packaging and a user-supplied System Card BIOS.

**Files:** `src/main.c` contains the topic-specific C sample; `src/demo_video.c` and `src/demo_video.h` provide the small SDK-backed screen fixture; `assets/demo_assets.h` contains its embedded tile/palette data, and `assets/demo.svg` is the editable source artwork. `assets/screenshot.png` is captured from the built ROM in the headless emulator. See additional files in this folder for topic-specific data.

Saber Rider stores eight active platform actors and a fixed shot pool. The actor update runs at a fixed frame cadence and dispatches by behavior: walkers turn at walls, grunts pause and fire once, snipers settle their aim before shooting, kneelers wind up a grenade, and shield enemies have distinct front/back damage behavior. Each actor owns its timer and animation state, so a behavior can resume without allocating memory during gameplay.

Shots share fixed-point movement but carry a type that selects their collision rules. Ordinary bullets stop on solid cells and special blocking tiles. Grenades follow a bounded arc, then become a stationary burst. Enemy bullets check the player's hit box only while the player is outside the invulnerability timer. Player bullets test active enemies, ignore cutscene-only actors, update shield state, and remove dead actors only after their death animation window.

## Order the frame deliberately

1. Update player movement and collision.
2. Update actor AI and spawn requests.
3. Advance projectiles and apply world collision.
4. Apply damage, invulnerability, death, and score/campaign state.
5. Admit sprites in visual-priority order and submit one SAT generation.

The PCE has a global SAT entry ceiling and a per-scanline sprite limit. Saber Rider admits the boss first, then enemies and their bullets, then the player's bullets and muzzle flash. Optional decorative sprites may be refused. An optional enemy that cannot be represented must not keep attacking invisibly; either despawn it, suspend its attacks, or reserve its full visual budget before enabling its hit box.

Allocate shot slots before reporting a successful shot. If the pool is full, do not play a muzzle sound or apply a hit for a projectile that does not exist. Conversely, once a damaging projectile has been admitted to simulation, dropping its cosmetic muzzle flash must not cancel its collision.

## Sprite-budget policy

- Count both total SAT entries and entries covering each scanline.
- Treat a wide sprite as its actual horizontal resource cost when the allocator uses width units.
- Reserve entries for essential actors and HUD before cosmetic effects.
- Keep a diagnostic counter for rejected essential sprites and test a crowded scene with all actors firing.
- Make collision participation follow the same eligibility state as the object design; visibility, invulnerability, and damage are separate flags.

The implementation paths are Saber Rider's world_update() in enemy_pce.c, shots_step() in shots_pce.c, player shooting in play_pce.c, and sprite admission in video_pce.c. The source game's enemy archetypes and exact hit boxes are adapted data, not universal PCE behavior.

`src/main.c` contains one enemy, one player shot, their hit check, and two SAT
slots. Extend its fixed pools and update order for a complete encounter.
