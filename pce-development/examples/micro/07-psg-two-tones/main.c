#include <pce.h>
int main(void) {
    pce_psg_reset();
    *IO_PSG_VOLUME = 0xff;
    for (uint8_t ch=0;ch<2;++ch) {
        *IO_PSG_CH_SELECT = ch;
        *IO_PSG_CH_CONTROL = PSG_CH_DDA;
        *IO_PSG_CH_CONTROL = 0;
        for (uint8_t i=0;i<32;++i) *IO_PSG_CH_SAMPLE = i<16 ? 31 : 0;
        *IO_PSG_CH_VOLUME = 0xff;
        *IO_PSG_CH_FREQ = ch ? 0x0180 : 0x0100;
        *IO_PSG_CH_CONTROL = PSG_CH_ON | 22;
    }
    for (;;) {}
}
