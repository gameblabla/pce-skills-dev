#include "../psg.h"
#include "../delay.h"
int main(void) {
    static const uint16_t notes[] = {0x0200,0x0180,0x0100};
    tone_init();
    for (;;) {
        for(uint8_t i=0;i<3;++i) {
            *IO_PSG_CH_FREQ = notes[i];
            pause_cpu(45000);
        }
    }
}
