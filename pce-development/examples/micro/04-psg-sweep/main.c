#include "../psg.h"
#include "../delay.h"
int main(void) {
    tone_init();
    for (;;) {
        for (uint16_t pitch = 0x100; pitch < 0x300; pitch += 8) {
            *IO_PSG_CH_FREQ = pitch;
            pause_cpu(2500);
        }
    }
}
