#include "../psg.h"
#include "../delay.h"
int main(void) {
    static const uint16_t periods[] = {0x01e0,0x01a0,0x0160,0x0140};
    tone_init();
    for (;;) {
        for (uint8_t i=0;i<4;++i) {
            *IO_PSG_CH_FREQ = periods[i];
            pause_cpu(40000);
        }
    }
}
