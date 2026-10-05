#define PCE_CONFIG_IMPLEMENTATION
#include <pce.h>
#include "demo_video.h"

PCE_ROM_BANK_AT(4, 3);
extern volatile uint8_t banked_result;
void banked_transform(void);

int main(void) {
    uint8_t previous_bank;
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    /* Map the worker at $6000, call it, then restore the previous MPR3 bank. */
    previous_bank = pce_bank3_get();
    pce_rom_bank4_map();
    banked_transform();
    pce_bank3_set(previous_bank);
    demo_set_color(0, 3, VCE_COLOR(banked_result & 7, 3, 7));
    for (;;) demo_wait_frame();
}
