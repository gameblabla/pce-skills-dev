#include "../psg.h"
int main(void) {
    tone_init();
    *IO_PSG_CH_FREQ = 0x0180;  /* channel 0 */
    *IO_PSG_CH_SELECT = 1;
    *IO_PSG_CH_CONTROL = PSG_CH_OFF; /* only channel 1 */
    *IO_PSG_CH_SELECT = 0;
    for (;;) {}
}
