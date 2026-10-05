#include <pce.h>
#include "demo_video.h"

int main(void) {
    /* Generated source.png pixels, palette and BAT are embedded in demo_assets.h. */
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) demo_wait_frame();
}
