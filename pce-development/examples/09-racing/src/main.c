#include <pce.h>
#include "demo_video.h"

int main(void) {
    uint16_t road_scroll = 0;
    demo_video_init(512, VCE_PIXEL_CLOCK_10MHZ);
    for (;;) {
        demo_wait_frame();
        road_scroll += 2;
        demo_set_scroll(road_scroll, 0);
    }
}
