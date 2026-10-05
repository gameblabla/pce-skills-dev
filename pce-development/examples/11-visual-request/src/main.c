#include <pce.h>
#include "demo_video.h"

typedef struct { uint8_t screen_x, screen_y; } HudAnchor;

int main(void) {
    int16_t actor_world_x = 64;
    const int16_t actor_world_y = 100;
    uint16_t camera_x = 0;
    HudAnchor hud = {16, 18};
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    demo_upload_sprite_patterns();
    demo_hide_sprite_slot(0);
    demo_hide_sprite_slot(1);
    for (;;) {
        uint8_t pad;
        demo_wait_frame();
        pad = pce_joypad_read();
        if (pad & KEY_RIGHT) ++actor_world_x;
        if (pad & KEY_LEFT) --actor_world_x;
        camera_x = actor_world_x > 160 ? (uint16_t)(actor_world_x - 160) : 0;
        if ((pad & KEY_1) && hud.screen_y > 0) --hud.screen_y;
        demo_set_scroll(camera_x, 0);
        demo_draw_sprite_slot(0, (int16_t)(actor_world_x - camera_x), actor_world_y,
                              0x0100, VDC_SPRITE_COLOR(1));
        demo_draw_sprite_slot(1, hud.screen_x, hud.screen_y, 0x0100,
                              VDC_SPRITE_COLOR(2));
    }
}
