/*
 * P2TR v1: game-authored, byte-stable platformer trace record.
 *
 * Define two consecutive volatile PcePlatformerTrace records named
 * pce_platformer_trace in the game. Update one record once per
 * gameplay frame, after physics/collision and after preparing the rendered
 * actor/platform geometry. Set reserved's low byte to an odd value before
 * writing fields, then publish the next even value after the final field. Keep
 * the other record unchanged until this publish completes, then swap which
 * record is active. The headless reader accepts the newest complete record.
 * These records are read-only tooling data in ordinary main RAM; they do not
 * add a hardware feature or change retail behavior.
 */
#ifndef PCE_PLATFORMER_TRACE_H
#define PCE_PLATFORMER_TRACE_H

#include <stdint.h>

#if defined(__GNUC__)
#define PCE_TRACE_PACKED __attribute__((packed))
#else
#define PCE_TRACE_PACKED
#endif

#define PCE_PLATFORM_TRACE_VERSION 1
#define PCE_PLATFORM_TRACE_SURFACES 4
#define PCE_PLATFORM_TRACE_BUFFER_COUNT 2
#define PCE_PLATFORM_TRACE_Q8(value) ((int32_t)(value) * 256L)

enum {
    PCE_TRACE_SCENE_TITLE = 0,
    PCE_TRACE_SCENE_PLAY = 1,
    PCE_TRACE_SCENE_DEATH = 2,
    PCE_TRACE_SCENE_WIN = 3
};

enum {
    PCE_TRACE_PLAYER_GROUNDED = 1u << 0,
    PCE_TRACE_PLAYER_DEAD = 1u << 1,
    PCE_TRACE_PLAYER_FACING_LEFT = 1u << 2,
    PCE_TRACE_PLAYER_BLOCKED_X = 1u << 3
};

enum {
    PCE_TRACE_EVENT_LANDED = 1u << 0,
    PCE_TRACE_EVENT_JUMPED = 1u << 1,
    PCE_TRACE_EVENT_STOMPED = 1u << 2,
    PCE_TRACE_EVENT_DIED = 1u << 3,
    PCE_TRACE_EVENT_RESPAWNED = 1u << 4,
    PCE_TRACE_EVENT_GOAL = 1u << 5
};

enum {
    PCE_TRACE_SURFACE_VALID = 1u << 0,
    PCE_TRACE_SURFACE_COLLIDABLE = 1u << 1,
    PCE_TRACE_SURFACE_ONE_WAY = 1u << 2
};

/* All coordinates, dimensions, and velocities are signed Q16.8 pixel values. */
typedef struct PCE_TRACE_PACKED {
    uint16_t id;
    uint8_t flags;
    uint8_t reserved;
    int32_t collision_x_q8;
    int32_t collision_y_q8;
    int32_t collision_w_q8;
    int32_t collision_h_q8;
    int32_t visual_x_q8;
    int32_t visual_y_q8;
    int32_t visual_w_q8;
    int32_t visual_h_q8;
} PcePlatformerTraceSurface;

typedef struct PCE_TRACE_PACKED {
    uint8_t magic[4];                 /* ASCII "P2TR" */
    uint8_t version;                  /* PCE_PLATFORM_TRACE_VERSION */
    uint8_t scene;                    /* PCE_TRACE_SCENE_* */
    uint8_t player_flags;             /* PCE_TRACE_PLAYER_* */
    uint8_t event_flags;              /* PCE_TRACE_EVENT_*; current frame only */
    uint8_t surface_count;            /* 0-4 valid records below */
    uint8_t sat_first;                /* first SAT index used by the protagonist */
    uint8_t sat_piece_count;          /* SAT entries used by the protagonist */
    uint8_t palette_index;            /* actual VCE palette selected for the actor */
    uint32_t game_frame;
    uint16_t buttons;                 /* active-high PCE pad bits, see the skill */
    uint16_t reserved;                /* low byte: even when complete, odd while writing; high byte zero */
    int32_t camera_x_q8;
    int32_t player_x_q8;              /* collision-box world-space top-left */
    int32_t player_y_q8;
    int32_t player_vx_q8;
    int32_t player_vy_q8;             /* positive moves down the screen */
    int32_t player_w_q8;
    int32_t player_h_q8;
    int32_t sprite_dx_q8;             /* visible sprite world x - collision x */
    int32_t sprite_dy_q8;             /* visible sprite world y - collision y */
    int32_t sprite_w_q8;              /* visible artwork bounds, not metasprite canvas */
    int32_t sprite_h_q8;
    int32_t draw_screen_x_q8;         /* visible top-left after camera and SAT bias */
    int32_t draw_screen_y_q8;
    PcePlatformerTraceSurface surfaces[PCE_PLATFORM_TRACE_SURFACES];
} PcePlatformerTrace;

/* Two consecutive records let the reader choose the latest completed publish. */
extern volatile PcePlatformerTrace pce_platformer_trace[PCE_PLATFORM_TRACE_BUFFER_COUNT];

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(PcePlatformerTraceSurface) == 36, "P2TR surface layout changed");
_Static_assert(sizeof(PcePlatformerTrace) == 216, "P2TR v1 layout changed");
#endif

#undef PCE_TRACE_PACKED
#endif
