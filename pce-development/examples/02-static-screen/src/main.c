#include <pce.h>
#include "demo_video.h"

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) demo_wait_frame();
}
