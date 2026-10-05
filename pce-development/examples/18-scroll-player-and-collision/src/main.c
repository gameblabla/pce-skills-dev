#include <pce.h>
#include "demo_video.h"

static uint8_t solid_at(int16_t world_x, int16_t world_y) {
    static const uint8_t wall_column = 24;
    static const uint8_t floor_row = 22;
    return (world_x / 8 == wall_column) || (world_y / 8 >= floor_row);
}

int main(void) {
    int16_t world_x = 64, world_y = 120;
    uint16_t camera_x = 0;
    demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);
    demo_upload_sprite_patterns();
    for (;;) {
        int16_t next_x, next_y;
        uint8_t pad;
        demo_wait_frame();
        pad = pce_joypad_read();
        next_x = world_x + ((pad & KEY_RIGHT) != 0) - ((pad & KEY_LEFT) != 0);
        next_y = world_y + ((pad & KEY_DOWN) != 0) - ((pad & KEY_UP) != 0);
        if (!solid_at(next_x, world_y)) world_x = next_x;
        if (!solid_at(world_x, next_y)) world_y = next_y;
        camera_x = world_x > 128 ? (uint16_t)(world_x - 128) : 0;
        demo_set_scroll(camera_x, 0);
        demo_draw_sprite((int16_t)(world_x - camera_x), world_y, 0x0100, VDC_SPRITE_COLOR(1));
    }
}
