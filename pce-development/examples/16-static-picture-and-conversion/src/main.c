#include <pce.h>
#include "demo_video.h"

int main(void) {
    /* The host picture converter's quantized tile fixture is mirrored in assets/demo_assets.h. */
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) demo_wait_frame();
}
