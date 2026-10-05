#include <pce.h>
#include "demo_video.h"

static void stream_column(uint8_t bat_column, uint16_t world_column) {
    static uint16_t column[32];
    for (uint8_t row = 0; row < 32; ++row)
        column[row] = demo_map_tile(world_column, row);
    pce_vdc_set_copy_column_64();
    /* The PC Engine BAT is fixed at VDC word address zero. */
    pce_vdc_copy_to_vram((uint16_t)bat_column, column, sizeof(column));
    pce_vdc_set_copy_word();
}

int main(void) {
    uint16_t camera_x = 0;
    uint16_t loaded_world_column = 0;
    demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);
    for (;;) {
        demo_wait_frame();
        camera_x += 1;
        if ((camera_x >> 3) != loaded_world_column) {
            uint16_t entering_column;
            loaded_world_column = camera_x >> 3;
            entering_column = (uint16_t)((camera_x + 255u) >> 3);
            stream_column((uint8_t)(entering_column & 63u), entering_column);
        }
        demo_set_scroll(camera_x, 0);
    }
}
