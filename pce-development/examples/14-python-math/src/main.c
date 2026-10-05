#include <pce.h>
#include "demo_video.h"
#include "calculation_result.h"

/* Put reviewed, Python-derived constants in a project header before use. */
static const uint16_t calculated_transfer_bytes = EXAMPLE_TRANSFER_BYTES;

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    demo_set_color(0, 1, VCE_COLOR(calculated_transfer_bytes & 7, 2, 6));
    for (;;) demo_wait_frame();
}
