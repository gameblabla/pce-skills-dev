#include <pce.h>
#include "demo_video.h"
#include "platformer_q4.h"
#include "../tools/p4tr.h"

/* Small world, 16-bit Q4 simulation, 32-byte trace publication. */
volatile P4Trace p4_trace[2];
static P4Motion player;
static uint16_t frame;
static uint8_t active,sequence;

int main(void) {
    p4_reset(&player);
    p4_events_reset();
    frame=0;active=0;sequence=0;
    p4_trace[0].sequence=1;p4_trace[1].sequence=1;
    demo_video_init(256,VCE_PIXEL_CLOCK_5MHZ);
    demo_upload_sprite_patterns();
    for (;;) {
        uint8_t pad,events,blocked;
        demo_wait_frame();
        pad=demo_read_pad();
        blocked=p4_tick(&player,pad,&events);
        demo_set_scroll((uint16_t)(player.camera/16),0);
        demo_draw_sprite_slot(0,(int16_t)((player.x-player.camera)/16),
            (int16_t)(player.y/16), DEMO_PLAYER_PATTERN,VDC_SPRITE_COLOR(1));
        ++frame;
        p4_publish(frame,0,pad,events,blocked,&player,0,0,&active,&sequence);
    }
}
