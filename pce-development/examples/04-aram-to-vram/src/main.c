#include <pce.h>
#include "demo_video.h"

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    /* demo_video_init uploads the source patterns and BAT from assets/ to VRAM. */
    for (;;) demo_wait_frame();
}
