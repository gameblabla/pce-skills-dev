/* G2TR v2 -- genre-neutral companion to legacy P2TR v1.
 * Two 64-byte records in normal PCE main RAM, updated alternately once/game tick.
 * Fields 0..7 are signed Q8 world or screen pixels; state[] are genre-defined.
 * The sequence is odd while writing and even when published. Do not call
 * game functions between marking an odd sequence and finishing the record.
 * Generic traces report game-authored facts, NOT evidence of rendered pixels.
 */
#ifndef PCE_GENRE_TRACE_H
#define PCE_GENRE_TRACE_H
#include <stdint.h>
#define G2TR_Q8(x) ((int32_t)(x) * 256L)
#define G2TR_VERSION 2
#define G2TR_PLATFORMER 1
#define G2TR_SHMUP 2
#define G2TR_RAYCASTER 3
#define G2TR_RACING 4
#define G2TR_VISUAL_NOVEL 5
#define G2TR_FLAG_VISIBLE 1
#define G2TR_FLAG_ACTIVE 2
#define G2TR_FLAG_COLLIDING 4
#define G2TR_FLAG_TRANSITION 8
#if defined(__GNUC__)
#define G2TR_PACKED __attribute__((packed))
#else
#define G2TR_PACKED
#endif
typedef struct G2TR_PACKED {
    uint8_t magic[4];        /* G2TR */
    uint8_t version;         /* 2 */
    uint8_t genre;           /* G2TR_* */
    uint8_t scene;           /* game-defined scene identifier */
    uint8_t flags;           /* generic visibility/activity bits */
    uint32_t frame;
    uint16_t buttons;        /* active-high PCE joypad bits */
    uint16_t sequence;       /* odd=incomplete, even=complete */
    int32_t x_q8, y_q8, vx_q8, vy_q8;
    int32_t camera_x_q8, camera_y_q8;
    int32_t screen_x_q8, screen_y_q8;
    int32_t state[4];
} G2Trace;
/* state interpretation:
 * shmup: live_bullets, live_enemies, shots_fired, damage_taken (integers)
 * raycaster: columns_cast, columns_hit, nearest_wall_q8, farthest_wall_q8
 * racing: lane_q8, distance_q8, forward_speed_q8, objects_visible (int)
 * visual novel: background_id, portrait_id, mouth_open(0/1), dialogue_id (int)
 * platformer: grounded(0/1), animation_id, collision_count, camera_lock
 */
extern volatile G2Trace pce_genre_trace[2];
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(G2Trace) == 64, "G2TR v2 must be 64 bytes");
#endif
#endif
