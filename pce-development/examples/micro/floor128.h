/* Tiny fixed-point Mode 7-style sampler for a 128x128 1-bit texture.
 * Follows Saber Rider's old PCE road principle: for each projected strip,
 * choose starting texture U/V and step along it across the screen.
 * Here a strip is one scanline, with Q7 integer coordinate stepping.
 * Not a native hardware Mode 7 mode, and not the original Arcade Card engine.
 */
#ifndef PCE_MICRO_FLOOR128_H
#define PCE_MICRO_FLOOR128_H
#include "bitmap128.h"

/* 16 camera directions, signed Q7 (range -127..127). */
static const int8_t floor128_sin[16] = {
      0, 49, 90,117,127,117, 90, 49,  0,-49,-90,-117,-127,-117,-90,-49
};
static const int8_t floor128_cos[16] = {
    127,117, 90, 49,  0,-49,-90,-117,-127,-117,-90, -49, 0, 49, 90,117
};

static void floor128_project(const uint8_t *texture, uint8_t *screen,
                             uint8_t angle) {
    const int16_t si = floor128_sin[angle & 15];
    const int16_t co = floor128_cos[angle & 15];
    bitmap128_clear(screen);
    for (uint8_t y = 0; y < 128; ++y) {
        /* Perspective: distant ground at the top, near ground at the bottom. */
        int16_t distance = (int16_t)(3072u / ((uint16_t)y + 28u));
        int16_t du = (co * distance) >> 6;
        int16_t dv = (si * distance) >> 6;
        int16_t u = (64 << 7) - si * distance - 64 * du;
        int16_t v = (16 << 7) + co * distance - 64 * dv;
        for (uint8_t x = 0; x < 128; ++x) {
            int16_t tx = u >> 7, ty = v >> 7;
            if ((uint16_t)tx < 128u && (uint16_t)ty < 128u &&
                (texture[((uint16_t)ty << 4) + ((uint8_t)tx >> 3)] &
                  (0x80u >> (tx & 7)))) {
                bitmap128_plot(screen, x, y);
            }
            u += du;
            v += dv;
        }
    }
}
#endif
