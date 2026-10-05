#include <pce.h>
#include "demo_video.h"

volatile uint8_t debug_marker;
volatile uint16_t debug_frames;

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) {
        demo_wait_frame();
        ++debug_frames;
        debug_marker = (uint8_t)(debug_frames & 0xff);
        demo_set_color(0, 3, VCE_COLOR(debug_marker & 7, (debug_marker >> 3) & 7, 2));
    }
}
