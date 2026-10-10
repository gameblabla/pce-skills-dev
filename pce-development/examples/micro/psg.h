/* Shared, tiny PSG waveform init; no screen state.
 * Call only when nothing else is using PSG channel 0. */
#ifndef PCE_MICRO_PSG_H
#define PCE_MICRO_PSG_H
#include <pce.h>
static void tone_init(void) {
    pce_psg_reset();
    *IO_PSG_VOLUME = 0xff;
    *IO_PSG_CH_SELECT = 0;
    *IO_PSG_CH_CONTROL = PSG_CH_DDA; /* reset waveform index */
    *IO_PSG_CH_CONTROL = 0;
    for (uint8_t i = 0; i < 32; ++i)
        *IO_PSG_CH_SAMPLE = (i < 16) ? 31 : 0;
    *IO_PSG_CH_VOLUME = 0xff; /* L/R balance */
    *IO_PSG_CH_CONTROL = PSG_CH_ON | 31;
}
#endif
