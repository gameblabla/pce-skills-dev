#include <pce.h>
#include "../delay.h"
int main(void) {
    pce_psg_reset();
    *IO_PSG_VOLUME=0xff;
    *IO_PSG_CH_SELECT=5;
    *IO_PSG_CH_VOLUME=0xff;
    *IO_PSG_CH_CONTROL=PSG_CH_ON | 28;
    for (;;) {
        *IO_PSG_CH_NOISE=PSG_CH_NOISE_ON | 0x18;
        pause_cpu(12000);
        *IO_PSG_CH_NOISE=PSG_CH_NOISE_OFF;
        pause_cpu(42000);
    }
}
