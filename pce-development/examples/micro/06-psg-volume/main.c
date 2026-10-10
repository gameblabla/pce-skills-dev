#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ = 0x0170;
    for (;;) {
        for (uint8_t v=31; v>0; --v) {
            *IO_PSG_CH_CONTROL = PSG_CH_ON | v;
            pause_cpu(2500);
        }
    }
}
