#include <pce.h>
#include "demo_video.h"
#include "../tools/platformer_trace.h"
#include "platform_layout.h"

#define Q8_PIXELS(value) PCE_PLATFORM_TRACE_Q8(value)
#define WORLD_WIDTH PCE_DEMO_WORLD_WIDTH
#define SCREEN_WIDTH 256
#define PLAYER_TILE_W 16
#define PLAYER_BOX_DX 3
#define PLAYER_BOX_DY 1
#define PLAYER_BOX_W 10
#define PLAYER_BOX_H 15
#define FLOOR_TOP PCE_DEMO_FLOOR_TOP
#define GRAVITY_Q8 64
#define JUMP_VELOCITY_Q8 (-1280)
#define WALK_SPEED_Q8 256
#define TERMINAL_VELOCITY_Q8 1536

#define PLATFORM_COUNT PCE_DEMO_SURFACE_COUNT

/* The symbol is resolved from the current ELF by `make trace`. */
volatile PcePlatformerTrace pce_platformer_trace[PCE_PLATFORM_TRACE_BUFFER_COUNT];

static int32_t player_sprite_x_q8;
static int32_t player_sprite_y_q8;
static int32_t player_vx_q8;
static int32_t player_vy_q8;
static int32_t camera_x_q8;
static uint32_t game_frame;
static uint8_t grounded = 1;
static uint8_t facing_left;
static uint8_t previous_jump;
static uint8_t trace_publish_sequence;
static uint8_t trace_active_index;

static void trace_surface(volatile PcePlatformerTrace *record, uint8_t slot,
                          const DemoPlatform *platform) {
    volatile PcePlatformerTraceSurface *trace = &record->surfaces[slot];
    trace->id = (uint16_t)(slot + 1u);
    trace->flags = PCE_TRACE_SURFACE_VALID | PCE_TRACE_SURFACE_COLLIDABLE |
                   PCE_TRACE_SURFACE_ONE_WAY;
    trace->reserved = 0;
    trace->collision_x_q8 = Q8_PIXELS(platform->x);
    trace->collision_y_q8 = Q8_PIXELS(platform->top);
    trace->collision_w_q8 = Q8_PIXELS(platform->width);
    trace->collision_h_q8 = Q8_PIXELS(platform->collision_height);
    trace->visual_x_q8 = Q8_PIXELS(platform->x);
    trace->visual_y_q8 = Q8_PIXELS(platform->top);
    trace->visual_w_q8 = Q8_PIXELS(platform->width);
    trace->visual_h_q8 = Q8_PIXELS(platform->art_height);
}

static uint8_t player_overlaps_surface_x(const DemoPlatform *platform) {
    const int32_t left = player_sprite_x_q8 + Q8_PIXELS(PLAYER_BOX_DX);
    const int32_t right = left + Q8_PIXELS(PLAYER_BOX_W);
    const int32_t surface_left = Q8_PIXELS(platform->x);
    const int32_t surface_right = surface_left + Q8_PIXELS(platform->width);
    return (uint8_t)(right > surface_left && left < surface_right);
}

static uint8_t player_supported(void) {
    const int32_t feet = player_sprite_y_q8 +
                         Q8_PIXELS(PLAYER_BOX_DY + PLAYER_BOX_H);
    uint8_t i;
    for (i = 0; i < PLATFORM_COUNT; ++i) {
        if (feet == Q8_PIXELS(pce_demo_surfaces[i].top) &&
            player_overlaps_surface_x(&pce_demo_surfaces[i]))
            return 1;
    }
    return 0;
}

static uint8_t update_player(uint8_t pad, uint8_t *events) {
    const int32_t previous_feet = player_sprite_y_q8 +
                                  Q8_PIXELS(PLAYER_BOX_DY + PLAYER_BOX_H);
    int32_t proposed_feet;
    uint8_t blocked_x = 0;
    uint8_t jump = (uint8_t)((pad & KEY_1) != 0);
    uint8_t i;

    *events = 0;
    if ((pad & KEY_LEFT) && !(pad & KEY_RIGHT)) {
        player_vx_q8 = -WALK_SPEED_Q8;
        facing_left = 1;
    } else if ((pad & KEY_RIGHT) && !(pad & KEY_LEFT)) {
        player_vx_q8 = WALK_SPEED_Q8;
        facing_left = 0;
    } else {
        player_vx_q8 = 0;
    }

    player_sprite_x_q8 += player_vx_q8;
    if (player_sprite_x_q8 < 0) {
        player_sprite_x_q8 = 0;
        blocked_x = 1;
    } else if (player_sprite_x_q8 > Q8_PIXELS(WORLD_WIDTH - PLAYER_TILE_W)) {
        player_sprite_x_q8 = Q8_PIXELS(WORLD_WIDTH - PLAYER_TILE_W);
        blocked_x = 1;
    }

    if (grounded && !player_supported()) grounded = 0;
    if (jump && !previous_jump && grounded) {
        player_vy_q8 = JUMP_VELOCITY_Q8;
        grounded = 0;
        *events |= PCE_TRACE_EVENT_JUMPED;
    }
    previous_jump = jump;

    if (!grounded) {
        player_vy_q8 += GRAVITY_Q8;
        if (player_vy_q8 > TERMINAL_VELOCITY_Q8)
            player_vy_q8 = TERMINAL_VELOCITY_Q8;
        player_sprite_y_q8 += player_vy_q8;
    } else {
        player_vy_q8 = 0;
    }

    proposed_feet = player_sprite_y_q8 +
                    Q8_PIXELS(PLAYER_BOX_DY + PLAYER_BOX_H);
    if (!grounded && player_vy_q8 >= 0) {
        for (i = 0; i < PLATFORM_COUNT; ++i) {
            const int32_t top = Q8_PIXELS(pce_demo_surfaces[i].top);
            if (previous_feet <= top && proposed_feet >= top &&
                player_overlaps_surface_x(&pce_demo_surfaces[i])) {
                player_sprite_y_q8 = top - Q8_PIXELS(PLAYER_BOX_DY + PLAYER_BOX_H);
                player_vy_q8 = 0;
                grounded = 1;
                *events |= PCE_TRACE_EVENT_LANDED;
                break;
            }
        }
    }

    return blocked_x;
}

static void update_camera(void) {
    const int32_t player_center = player_sprite_x_q8 + Q8_PIXELS(PLAYER_TILE_W / 2);
    const int32_t camera_limit = Q8_PIXELS(WORLD_WIDTH - SCREEN_WIDTH);
    camera_x_q8 = player_center > Q8_PIXELS(112)
        ? player_center - Q8_PIXELS(112) : 0;
    if (camera_x_q8 > camera_limit) camera_x_q8 = camera_limit;
}

static void publish_trace(uint8_t pad, uint8_t events, uint8_t blocked_x,
                          int16_t sprite_screen_x, int16_t sprite_screen_y) {
    const int32_t box_x = player_sprite_x_q8 + Q8_PIXELS(PLAYER_BOX_DX);
    const int32_t box_y = player_sprite_y_q8 + Q8_PIXELS(PLAYER_BOX_DY);
    const uint8_t write_index = (uint8_t)(trace_active_index ^ 1u);
    volatile PcePlatformerTrace *trace = &pce_platformer_trace[write_index];
    uint8_t i;

    trace_publish_sequence = (uint8_t)((trace_publish_sequence + 2u) & 0xFEu);
    trace->reserved = (uint16_t)(trace_publish_sequence | 1u);
    trace->magic[0] = 'P';
    trace->magic[1] = '2';
    trace->magic[2] = 'T';
    trace->magic[3] = 'R';
    trace->version = PCE_PLATFORM_TRACE_VERSION;
    trace->scene = PCE_TRACE_SCENE_PLAY;
    trace->player_flags = (grounded ? PCE_TRACE_PLAYER_GROUNDED : 0) |
        (facing_left ? PCE_TRACE_PLAYER_FACING_LEFT : 0) |
        (blocked_x ? PCE_TRACE_PLAYER_BLOCKED_X : 0);
    trace->event_flags = events;
    trace->surface_count = PLATFORM_COUNT;
    trace->sat_first = 0;
    trace->sat_piece_count = 1;
    trace->palette_index = 1;
    trace->game_frame = game_frame;
    trace->buttons = pad;
    trace->camera_x_q8 = camera_x_q8;
    trace->player_x_q8 = box_x;
    trace->player_y_q8 = box_y;
    trace->player_vx_q8 = player_vx_q8;
    trace->player_vy_q8 = player_vy_q8;
    trace->player_w_q8 = Q8_PIXELS(PLAYER_BOX_W);
    trace->player_h_q8 = Q8_PIXELS(PLAYER_BOX_H);
    trace->sprite_dx_q8 = 0;
    trace->sprite_dy_q8 = 0;
    trace->sprite_w_q8 = Q8_PIXELS(PLAYER_BOX_W);
    trace->sprite_h_q8 = Q8_PIXELS(PLAYER_BOX_H);
    /* The visible 10x15 art bounds are inset 3,1 pixels into the 16x16 SAT tile,
       exactly matching the collision box. Record the submitted integer SAT
       position plus that visible-art inset, after the integer scroll offset. */
    trace->draw_screen_x_q8 =
        Q8_PIXELS(sprite_screen_x + PLAYER_BOX_DX);
    trace->draw_screen_y_q8 =
        Q8_PIXELS(sprite_screen_y + PLAYER_BOX_DY);
    for (i = 0; i < trace->surface_count; ++i)
        trace_surface(trace, i, &pce_demo_surfaces[i]);
    trace->reserved = trace_publish_sequence;
    trace_active_index = write_index;
}

int main(void) {
    /* Assign gameplay state explicitly; do not depend on ROM-to-RAM .data copy
       for initialized globals on the bare-metal target. */
    player_sprite_x_q8 = Q8_PIXELS(32);
    player_sprite_y_q8 = Q8_PIXELS(FLOOR_TOP - PLAYER_TILE_W);
    player_vx_q8 = 0;
    player_vy_q8 = 0;
    camera_x_q8 = 0;
    game_frame = 0;
    grounded = 1;
    facing_left = 0;
    previous_jump = 0;
    trace_publish_sequence = 0;
    trace_active_index = 0;
    pce_platformer_trace[0].reserved = 0;
    pce_platformer_trace[1].reserved = 0;
    demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);
    demo_upload_sprite_patterns();
    for (;;) {
        uint8_t pad;
        uint8_t events;
        uint8_t blocked_x;
        int16_t sprite_screen_x;
        int16_t sprite_screen_y;
        demo_wait_frame();
        pad = demo_read_pad();
        blocked_x = update_player(pad, &events);
        update_camera();
        demo_set_scroll((uint16_t)(camera_x_q8 >> 8), 0);
        sprite_screen_x = (int16_t)((player_sprite_x_q8 >> 8) - (camera_x_q8 >> 8));
        sprite_screen_y = (int16_t)(player_sprite_y_q8 >> 8);
        demo_draw_sprite_slot(0, sprite_screen_x, sprite_screen_y,
            DEMO_PLAYER_PATTERN, VDC_SPRITE_COLOR(1));
        ++game_frame;
        publish_trace(pad, events, blocked_x, sprite_screen_x, sprite_screen_y);
    }
}
