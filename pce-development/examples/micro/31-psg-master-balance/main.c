#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ = 0x0180;
    for (;;) {
        *IO_PSG_VOLUME = 0xf0; /* left only */
        pause_cpu(45000);
        *IO_PSG_VOLUME = 0x0f; /* right only */
        pause_cpu(45000);
    }
}
