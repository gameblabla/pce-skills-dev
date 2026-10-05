#include <pce.h>
#include "demo_video.h"

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    demo_upload_sprite_patterns();
    demo_draw_sprite(144, 96, DEMO_PLAYER_PATTERN, VDC_SPRITE_COLOR(1));
    for (;;) demo_wait_frame();
}
