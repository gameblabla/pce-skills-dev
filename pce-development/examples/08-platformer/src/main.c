#include <pce.h>
#include "demo_video.h"

int main(void) {
    int16_t world_x = 64;
    uint16_t camera_x = 0;
    demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);
    demo_upload_sprite_patterns();
    for (;;) {
        uint8_t pad;
        demo_wait_frame();
        pad = demo_read_pad();
        if ((pad & KEY_LEFT) && world_x > 0) --world_x;
        if ((pad & KEY_RIGHT) && world_x < 480) ++world_x;
        camera_x = world_x > 128 ? (uint16_t)(world_x - 128) : 0;
        demo_set_scroll(camera_x, 0);
        demo_draw_sprite((int16_t)(world_x - camera_x), 160, DEMO_PLAYER_PATTERN, VDC_SPRITE_COLOR(1));
    }
}
