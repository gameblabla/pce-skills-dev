#include <pce.h>
int main(void) {
    static const uint8_t wave[16] = {16,22,27,30,31,30,27,22,16,10,5,2,0,2,5,10};
    pce_psg_reset();
    *IO_PSG_VOLUME = 0xff;
    *IO_PSG_CH_SELECT = 4;
    *IO_PSG_CH_VOLUME = 0xff;
    *IO_PSG_CH_CONTROL = PSG_CH_ON | PSG_CH_DDA | 31;
    for (;;) {
        for(uint8_t i=0;i<16;++i) *IO_PSG_CH_SAMPLE = wave[i];
    }
}
