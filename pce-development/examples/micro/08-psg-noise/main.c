#include <pce.h>
int main(void) {
    pce_psg_reset();
    *IO_PSG_VOLUME = 0xff;
    *IO_PSG_CH_SELECT = 4;
    *IO_PSG_CH_VOLUME = 0xff;
    *IO_PSG_CH_NOISE = PSG_CH_NOISE_ON | 17;
    *IO_PSG_CH_CONTROL = PSG_CH_ON | 25;
    for (;;) {}
}
