#include <pce.h>
#include "demo_video.h"

typedef struct { int16_t x, y; uint8_t active; } Shot;

int main(void) {
    Shot shots[4] = {{0}};
    uint8_t next = 0;
    demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);
    demo_upload_sprite_patterns();
    for (uint8_t i = 0; i < 4; ++i) demo_hide_sprite_slot(i);
    demo_draw_sprite_slot(4, 120, 176, DEMO_PLAYER_PATTERN, VDC_SPRITE_COLOR(1));
    for (;;) {
        uint8_t pad;
        demo_wait_frame();
        pad = demo_read_pad();
        if (pad & KEY_1) {
            shots[next].x = 120; shots[next].y = 170; shots[next].active = 1;
            next = (uint8_t)((next + 1) & 3);
        }
        for (uint8_t i = 0; i < 4; ++i) {
            if (shots[i].active) {
                --shots[i].y;
                if (shots[i].y < 0) shots[i].active = 0;
            }
            if (shots[i].active)
                demo_draw_sprite_slot(i, shots[i].x, shots[i].y, DEMO_SHOT_PATTERN, VDC_SPRITE_COLOR(2));
            else
                demo_hide_sprite_slot(i);
        }
    }
}
