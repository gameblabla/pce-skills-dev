#include <pce.h>

/* Small PSG tone example: audio only. No VDC/VCE/fonts/graphics. */
int main(void) {
    pce_psg_reset();
    *IO_PSG_VOLUME = 0xff;
    *IO_PSG_CH_SELECT = 0;
    *IO_PSG_CH_CONTROL = PSG_CH_DDA; /* reset waveform write index */
    *IO_PSG_CH_CONTROL = PSG_CH_OFF;
    for (uint8_t i = 0; i < 32; ++i)
        *IO_PSG_CH_SAMPLE = (i < 16) ? 31 : 0;
    *IO_PSG_CH_VOLUME = 0xff;
    *IO_PSG_CH_FREQ = 0x0180;
    *IO_PSG_CH_CONTROL = PSG_CH_ON | 31;
    for (;;) {}
}
