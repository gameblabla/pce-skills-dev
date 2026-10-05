#include <pce.h>
#include "demo_video.h"

int main(void) {
    demo_video_init(512, VCE_PIXEL_CLOCK_10MHZ);
    demo_enable_parallax_bands();
    for (;;) {
        demo_wait_frame();
        /* Rebuild road offsets here from world speed; the IRQ applies each band. */
    }
}
