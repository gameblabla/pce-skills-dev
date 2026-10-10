#include <pce.h>
#include "../delay.h"
int main(void) {
    pce_psg_reset();
    *IO_PSG_VOLUME = 0xff;
    *IO_PSG_CH_SELECT = 4;
    *IO_PSG_CH_VOLUME = 0xff;
    *IO_PSG_CH_NOISE = PSG_CH_NOISE_ON | 24;
    *IO_PSG_CH_CONTROL = PSG_CH_ON | 31;
    pause_cpu(55000);
    *IO_PSG_CH_CONTROL = PSG_CH_OFF;
    for (;;) {}
}
