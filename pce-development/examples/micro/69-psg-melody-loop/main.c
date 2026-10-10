#include "../psg.h"
#include "../delay.h"
int main(void) {
    static const uint16_t notes[4]={0x0200,0x0180,0x0140,0x0180};
    tone_init();
    for (;;) for(uint8_t n=0;n<4;++n) {
        *IO_PSG_CH_FREQ=notes[n];
        pause_cpu(55000);
    }
}
