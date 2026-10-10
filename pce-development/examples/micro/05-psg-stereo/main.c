#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ = 0x0120;
    for (;;) {
        *IO_PSG_CH_VOLUME = 0xf0;
        pause_cpu(30000);
        *IO_PSG_CH_VOLUME = 0x0f;
        pause_cpu(30000);
    }
}
