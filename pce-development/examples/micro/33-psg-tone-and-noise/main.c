#include "../psg.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ = 0x0180; /* channel 0 */
    *IO_PSG_CH_SELECT = 5;
    *IO_PSG_CH_VOLUME = 0xff;
    *IO_PSG_CH_NOISE = PSG_CH_NOISE_ON | 14;
    *IO_PSG_CH_CONTROL = PSG_CH_ON | 10;
    for (;;) {}
}
