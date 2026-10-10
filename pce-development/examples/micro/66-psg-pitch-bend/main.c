#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    for (;;) for(uint16_t period=0x0100;period<0x0300;period+=8) {
        *IO_PSG_CH_FREQ=period;
        pause_cpu(8000);
    }
}
