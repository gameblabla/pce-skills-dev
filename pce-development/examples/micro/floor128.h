/* Perspective texture projection into PCEdev's VRAM/BAT pseudo-bitmap.
 * The 128x128 logical pixels are written as 64 *packed BAT words* per row.
 * No per-frame pattern uploads; the 256 patterns never change after setup.
 * Original Saber Rider floor_sampler used this pair format too, but cached
 * 19 strips/double BAT pages and sourced textures from Arcade Card RAM.
 */
#ifndef PCE_MICRO_FLOOR128_H
#define PCE_MICRO_FLOOR128_H
#include "bat_bitmap.h"
static const int8_t floor_sin[16] = {
    0,49,90,117,127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49
};
static const int8_t floor_cos[16] = {
    127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49,0,49,90,117
};
/* A small repeating track: source texels are indices into a 16-colour VCE
 * palette. Its curves, kerbs and markings make rotation easy to recognize.
 */
static uint8_t floor_texel(uint8_t x, uint8_t y) {
    static const int8_t bends[16] = {
        0,3,6,10,12,13,11,7,2,-4,-9,-12,-11,-7,-3,0
    };
    int16_t side = (int16_t)x - (64 + bends[y >> 3]);
    uint8_t delta = (uint8_t)(side < 0 ? -side : side);
    if (delta < 20) {
        if (delta >= 16) return (y & 8) ? 14 : 13; /* kerb */
        if (delta < 2 && (y & 31) < 18) return 15; /* yellow dash */
        if ((y & 15) == 0) return 10;              /* road seam */
        return ((x ^ y) & 8) ? 11 : 12;            /* asphalt */
    }
    /* Grass variation stays green: no cyan marker pixels/holes. */
    if ((x & 31) < 2 && (y & 31) < 2) return 9;
    if (((x ^ y) & 31) < 3) return 7;
    if ((x & 16) && (y & 16)) return 8;
    return (((x >> 3) ^ (y >> 3)) & 1) ? 8 : 9;
}
static void floor_setup(void) {
    /* Seven monotonically brightening sky colours, then nine terrain
     * colours. Colour 0 also sets the VCE backdrop (see bat_bitmap.h). */
    static const uint16_t colors[16] = {
        VCE_COLOR(0,0,2), VCE_COLOR(0,0,3), VCE_COLOR(0,1,4),
        VCE_COLOR(0,2,5), VCE_COLOR(1,3,6), VCE_COLOR(2,4,7),
        VCE_COLOR(4,6,7),
        VCE_COLOR(0,2,0), VCE_COLOR(0,3,0), VCE_COLOR(1,5,1),
        VCE_COLOR(5,5,5), VCE_COLOR(2,2,2), VCE_COLOR(3,3,3),
        VCE_COLOR(7,7,7), VCE_COLOR(7,1,1), VCE_COLOR(7,7,0)
    };
    bat_bitmap_setup(colors);
}
static void floor_draw(uint8_t angle,uint8_t cx,uint8_t cy) {
    int16_t cs=floor_cos[angle&15u], sn=floor_sin[angle&15u];
    for (uint8_t y=0; y<128u; ++y) {
        bat_bitmap_row(y);
        if (y<35u) {
            /* Seven-step gradient, darkest at top and palest at horizon.
             * Keep every row monotonic: no alternating bars. */
            uint8_t sky=(uint8_t)(((uint16_t)y*7u)/35u);
            for (uint8_t pair=0; pair<64; ++pair)
                bat_bitmap_pair(sky,sky);
        } else {
            uint16_t distance=(uint16_t)(1408u/(uint16_t)(y-27u));
            int16_t du=(int16_t)((cs*(int16_t)distance)/64);
            int16_t dv=(int16_t)((sn*(int16_t)distance)/64);
            uint16_t u=((uint16_t)cx<<7)-(int16_t)(sn*distance)-(int16_t)(du*64);
            uint16_t v=((uint16_t)cy<<7)+(int16_t)(cs*distance)-(int16_t)(dv*64);
            for (uint8_t pair=0; pair<64; ++pair) {
                uint8_t a=floor_texel((uint8_t)((u>>7)&127u),(uint8_t)((v>>7)&127u));
                u+=du; v+=dv;
                uint8_t b=floor_texel((uint8_t)((u>>7)&127u),(uint8_t)((v>>7)&127u));
                u+=du; v+=dv;
                bat_bitmap_pair(a,b);
            }
        }
    }
}
#endif
