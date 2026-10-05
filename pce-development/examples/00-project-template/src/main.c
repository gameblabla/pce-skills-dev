#include <pce.h>
#include "demo_video.h"

int main(void) {
    demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);
    for (;;) {
        demo_wait_frame();
        demo_set_color(0, 3, VCE_COLOR((demo_vblank_count >> 3) & 7, 3, 7));
    }
}
