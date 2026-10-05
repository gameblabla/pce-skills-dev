#include <pce.h>
#include "demo_video.h"

int main(void) {
    uint8_t frame = 0;
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    demo_upload_sprite_patterns();
    for (;;) {
        uint16_t pose;
        demo_wait_frame();
        pose = (uint16_t)(DEMO_POSE_PATTERN + ((frame++ >> 4) & 1u) * 8u);
        /* Both complete poses are resident; only publish the next SAT references. */
        for (uint8_t cell = 0; cell < 4; ++cell)
            demo_draw_sprite_slot(cell, (int16_t)(144 + (cell & 1u) * 16),
                                  (int16_t)(96 + (cell >> 1) * 16),
                                  (uint16_t)(pose + cell * 2u), VDC_SPRITE_COLOR(1));
    }
}
