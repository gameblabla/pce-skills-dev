#include <pce.h>
#include "demo_video.h"

int main(void) {
    uint16_t width = 320;
    uint8_t clock = VCE_PIXEL_CLOCK_7MHZ;
    uint8_t previous_pad = 0;
    demo_video_init(width, clock);
    for (;;) {
        uint8_t pad;
        demo_wait_frame();
        pad = demo_read_pad();
        if ((pad & KEY_1) && !(previous_pad & KEY_1)) {
            if (width == 320) { width = 512; clock = VCE_PIXEL_CLOCK_10MHZ; }
            else { width = 320; clock = VCE_PIXEL_CLOCK_7MHZ; }
            demo_video_init(width, clock);
        }
        previous_pad = pad;
    }
}
