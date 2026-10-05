#define PCE_CONFIG_IMPLEMENTATION
#include <pce.h>
#include "demo_video.h"

PCE_RAM_BANK_AT(1, 3);
extern volatile uint8_t banked_result;
void banked_transform(void);

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    /* The SDK callback maps the declared bank, calls the function, then restores MPR3. */
    pce_ram_bank1_call(banked_transform);
    demo_set_color(0, 1, VCE_COLOR(banked_result & 7, 3, 7));
    for (;;) demo_wait_frame();
}
