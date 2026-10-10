#include <pce.h>
#include "../delay.h"
int main(void) {
    pce_psg_reset();
    *IO_PSG_VOLUME=0xff;
    *IO_PSG_CH_SELECT=5;
    *IO_PSG_CH_VOLUME=0xff;
    *IO_PSG_CH_CONTROL=PSG_CH_ON | 31;
    for(;;) {
        for(uint8_t n=0;n<32;++n) {
            *IO_PSG_CH_NOISE=PSG_CH_NOISE_ON | n;
            pause_cpu(7000);
        }
    }
}
