#include <pce.h>
#include "demo_video.h"

typedef struct { int16_t x, y; uint8_t alive; } Actor;
typedef struct { int16_t x, y; uint8_t active; } Shot;

int main(void) {
    Actor enemy = {180, 80, 1};
    Shot shot = {0, 0, 0};
    demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);
    demo_upload_sprite_patterns();
    demo_hide_sprite_slot(0);
    demo_hide_sprite_slot(1);
    for (;;) {
        demo_wait_frame();
        if (pce_joypad_read() & KEY_1) { shot.x = 120; shot.y = enemy.y + 8; shot.active = 1; }
        if (shot.active) {
            ++shot.x;
            if (enemy.alive && shot.x >= enemy.x && shot.y >= enemy.y && shot.y < enemy.y + 16) {
                enemy.alive = 0;
                shot.active = 0;
            }
            if (shot.x > 300) shot.active = 0;
        }
        if (enemy.alive)
            demo_draw_sprite_slot(0, enemy.x, enemy.y, 0x0100, VDC_SPRITE_COLOR(1));
        else
            demo_hide_sprite_slot(0);
        if (shot.active)
            demo_draw_sprite_slot(1, shot.x, shot.y, 0x0100, VDC_SPRITE_COLOR(2));
        else
            demo_hide_sprite_slot(1);
    }
}
