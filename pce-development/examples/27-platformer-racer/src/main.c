#include <pce.h>
#include "demo_video.h"
#include "platformer_q4.h"
#include "hybrid_rules.h"
#include "../tools/p4tr.h"

volatile P4Trace p4_trace[2];
volatile uint8_t hybrid_scene;  /* 0 platformer, 1 racer */
volatile uint16_t hybrid_race_progress_px;
volatile uint16_t hybrid_race_lane_px;
static P4Motion player;
static uint16_t frame,race_frame;
static uint8_t active,sequence;

static void enter_race(void) {
    hybrid_scene=1;
    p4_events_reset();
    hybrid_race_progress_px=0;
    hybrid_race_lane_px=(HYBRID_LANE_MIN+HYBRID_LANE_MAX)/2;
    race_frame=0;
    demo_load_race_background();
    demo_hide_sprite_slot(1);
}
static void enter_platformer(void) {
    hybrid_scene=0;
    p4_events_reset();
    p4_reset(&player);
    demo_restore_platform_background();
    demo_hide_sprite_slot(1);
    demo_set_scroll(0,0);
    demo_draw_sprite_slot(0,32,PCE_DEMO_FLOOR_TOP-P4_PLAYER_W,
                          DEMO_PLAYER_PATTERN,VDC_SPRITE_COLOR(1));
}
static void race_tick(uint8_t pad) {
    uint16_t lane=hybrid_race_lane_px;
    if((pad&KEY_LEFT)&&!(pad&KEY_RIGHT))lane=(lane>HYBRID_LANE_MIN+2)?lane-2:HYBRID_LANE_MIN;
    if((pad&KEY_RIGHT)&&!(pad&KEY_LEFT))lane=(lane<HYBRID_LANE_MAX-2)?lane+2:HYBRID_LANE_MAX;
    hybrid_race_lane_px=lane;
    if(pad&KEY_UP)hybrid_race_progress_px+=(HYBRID_RACE_SPEED_Q8/256);
    ++race_frame;
    demo_set_scroll((uint16_t)((race_frame>>2)&63u),0);
    demo_draw_sprite_slot(0,(int16_t)lane,172,DEMO_PLAYER_PATTERN,VDC_SPRITE_COLOR(1));
    demo_draw_sprite_slot(1,120,(int16_t)(72+((hybrid_race_progress_px>>1)&63u)),
                          DEMO_ENEMY_PATTERN,VDC_SPRITE_COLOR(2));
    if(hybrid_race_progress_px>=HYBRID_FIRST_RACE_LENGTH)enter_platformer();
}
int main(void) {
    frame=0;active=0;sequence=0;race_frame=0;
    p4_events_reset();
    p4_trace[0].sequence=1;p4_trace[1].sequence=1;
    demo_video_init(256,VCE_PIXEL_CLOCK_5MHZ);
    demo_upload_sprite_patterns();
    enter_platformer();
    for(;;) {
        uint8_t pad,events=0,blocked=0;

        demo_wait_frame();

        pad=demo_read_pad();

        if(hybrid_scene) {
            race_tick(pad);
        } else {
            blocked=p4_tick(&player,pad,&events);
            if(player.x>=P4(HYBRID_FIRST_PLATFORM_LENGTH)) {
                enter_race();
            } else {

                demo_set_scroll((uint16_t)(player.camera/16),0);


                demo_draw_sprite_slot(0,(int16_t)((player.x-player.camera)/16),
                      (int16_t)(player.y/16),DEMO_PLAYER_PATTERN,VDC_SPRITE_COLOR(1));

            }
        }

        ++frame;
        p4_publish(frame,hybrid_scene,pad,events,blocked,&player,
                   hybrid_race_lane_px,hybrid_race_progress_px,&active,&sequence);

    }
}
