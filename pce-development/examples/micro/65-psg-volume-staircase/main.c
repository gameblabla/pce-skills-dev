#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ=0x0180;
    for (;;) for(uint8_t volume=1;volume<32;volume+=4) {
        *IO_PSG_CH_CONTROL=PSG_CH_ON | volume;
        pause_cpu(25000);
    }
}
