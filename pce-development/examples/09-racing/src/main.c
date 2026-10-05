#include <pce.h>
#include "demo_video.h"

int main(void) {
    uint8_t stripe = 0;
    demo_video_init(512, VCE_PIXEL_CLOCK_10MHZ);
    demo_upload_sprite_patterns();
    demo_draw_sprite(248, 184, DEMO_PLAYER_PATTERN, VDC_SPRITE_COLOR(1));
    for (;;) {
        demo_wait_frame();
        /* Palette animation marks motion without scrolling the perspective. */
        demo_set_color(0, 4, (++stripe & 16) ? VCE_COLOR(7,6,1) : VCE_COLOR(7,7,7));
    }
}
