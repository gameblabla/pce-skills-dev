/* Deliberately approximate CPU busy-wait for standalone demos, not audio-rate timing.
 * No VDC, VCE, video IRQ, sprite, or font setup is required. */
#ifndef PCE_MICRO_DELAY_H
#define PCE_MICRO_DELAY_H
#include <stdint.h>
static void pause_cpu(uint16_t count) {
    volatile uint16_t i = count;
    while (i--) { __asm__ volatile("nop"); }
}
#endif
