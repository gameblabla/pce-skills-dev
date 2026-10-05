#include <pce.h>
#include "demo_video.h"

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    demo_draw_bitmap_text_pce();
    for (;;) demo_wait_frame();
}
