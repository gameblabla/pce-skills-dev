#include <pce.h>
#include "demo_video.h"
#include "demo_assets.h"

int main(void) {
    uint8_t frame = 0;
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) {
        demo_wait_frame();
        pce_vdc_copy_to_vram(0x0800,
            (frame++ & 1) ? &pce_demo_patterns[32] : &pce_demo_patterns[64], 32);
    }
}
