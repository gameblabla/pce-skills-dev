#include "../psg.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ = 0x0180;
    for (;;) {}
}
