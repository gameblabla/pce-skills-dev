# Example 19: enemies, projectiles, and hit rules

**Build contract:** Use fixed-capacity actor and projectile pools sized from the active game's worst case. The Saber Rider counts below describe its current port, not a general PCE limit.

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
