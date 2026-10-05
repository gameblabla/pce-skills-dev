#include <pce.h>
#include "demo_video.h"

int main(void) {
    static const uint8_t dda_wave[] = {0, 8, 16, 24, 31, 24, 16, 8};
    uint8_t index = 0;
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    pce_psg_reset();
    *IO_PSG_CH_SELECT = 4;
    *IO_PSG_CH_CONTROL = 0;
    *IO_PSG_CH_VOLUME = 0xff;
    *IO_PSG_CH_CONTROL = 0xdf;
    for (;;) {
        demo_wait_frame();
        *IO_PSG_CH_SELECT = 4;
        *IO_PSG_CH_SAMPLE = dda_wave[index++ & 7];
    }
}
