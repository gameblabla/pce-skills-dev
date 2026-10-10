#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ=0x0180;
    for (;;) {
        *IO_PSG_CH_CONTROL=PSG_CH_DDA;
        *IO_PSG_CH_CONTROL=0;
        for(uint8_t i=0;i<32;++i) *IO_PSG_CH_SAMPLE=i<8?31:0;
        *IO_PSG_CH_CONTROL=PSG_CH_ON | 31;
        pause_cpu(50000);
        *IO_PSG_CH_CONTROL=PSG_CH_DDA;
        *IO_PSG_CH_CONTROL=0;
        for(uint8_t i=0;i<32;++i) *IO_PSG_CH_SAMPLE=i<16?31:0;
        *IO_PSG_CH_CONTROL=PSG_CH_ON | 31;
        pause_cpu(50000);
    }
}
