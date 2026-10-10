#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ = 0x0150;
    pause_cpu(60000);
    *IO_PSG_CH_CONTROL = PSG_CH_OFF;
    for (;;) {}
}
