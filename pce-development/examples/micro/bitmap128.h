/* Minimal 128x128, 1-bit software bitmap displayed as 4bpp PCE BG tiles.
 * 2048-byte RAM image. Palette 0 = black, palette 1 = red.
 * The HuC6270 has NO packed-pixel bitmap mode: conversion happens at upload.
 * Graphics ONLY: no PSG, sound, fonts, sprites or game framework.
 */
#ifndef PCE_MICRO_BITMAP128_H
#define PCE_MICRO_BITMAP128_H
#include <pce.h>

#define BITMAP128_BYTES 2048u
#define BITMAP128_PATTERN_WORD 0x0800u

static void bitmap128_clear(uint8_t *bits) {
    for (uint16_t i = 0; i < BITMAP128_BYTES; ++i) bits[i] = 0;
}
static void bitmap128_plot(uint8_t *bits, uint8_t x, uint8_t y) {
    bits[((uint16_t)y << 4) + (x >> 3)] |= (uint8_t)(0x80u >> (x & 7));
}
static void bitmap128_span(uint8_t *bits, int16_t y, int16_t a, int16_t b) {
    if (y < 0 || y >= 128) return;
    if (a < 0) a = 0;
    if (b > 127) b = 127;
    for (int16_t x = a; x <= b; ++x) bitmap128_plot(bits, (uint8_t)x, (uint8_t)y);
}
/* Filled circle using integer midpoint steps; no multiplications, floats or assets. */
static void bitmap128_circle(uint8_t *bits, int16_t cx, int16_t cy, int16_t r) {
    int16_t x = r, y = 0, error = 1 - r;
    while (x >= y) {
        bitmap128_span(bits, cy + y, cx - x, cx + x);
        bitmap128_span(bits, cy - y, cx - x, cx + x);
        bitmap128_span(bits, cy + x, cx - y, cx + y);
        bitmap128_span(bits, cy - x, cx - y, cx + y);
        ++y;
        if (error < 0) error += 2 * y + 1;
        else { --x; error += 2 * (y - x) + 1; }
    }
}
static void bitmap128_screen(void) {
    static const uint8_t blank[32] = {0};
    pce_vdc_bg_disable();
    pce_vdc_set_resolution(256, 224, VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);
    pce_vdc_set_copy_word();
    pce_vce_set_color(0, VCE_COLOR(0, 0, 0));
    pce_vce_set_color(1, VCE_COLOR(7, 0, 0));
    pce_vdc_copy_to_vram(0x0400, blank, sizeof(blank));
    /* 16x16 BG characters make a 128x128 pixel window at (64,48). */
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR, 0);
    *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
    for (uint16_t y = 0; y < 32; ++y)
        for (uint16_t x = 0; x < 32; ++x) {
            uint16_t character = 0x40;
            if (x >= 8 && x < 24 && y >= 6 && y < 22)
                character = 0x80 + (y - 6) * 16 + x - 8;
            *IO_VDC_DATA = character;
        }
}
/* Each 8-pixel packed row becomes VDC plane 0; planes 1-3 are zero. */
static void bitmap128_present(const uint8_t *bits) {
    for (uint8_t ty = 0; ty < 16; ++ty)
        for (uint8_t tx = 0; tx < 16; ++tx) {
            uint16_t address = BITMAP128_PATTERN_WORD + ((uint16_t)ty * 16 + tx) * 16;
            pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR, address);
            *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
            for (uint8_t row = 0; row < 8; ++row)
                *IO_VDC_DATA = bits[((uint16_t)(ty * 8 + row) << 4) + tx];
            for (uint8_t row = 0; row < 8; ++row)
                *IO_VDC_DATA = 0;
        }
}
#endif
