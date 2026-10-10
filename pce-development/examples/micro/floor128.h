/* Perspective texture projection into PCEdev's VRAM/BAT pseudo-bitmap.
 * The 128x128 logical pixels are written as 64 *packed BAT words* per row.
 * No per-frame pattern uploads; the 256 patterns never change after setup.
 * Original Saber Rider floor_sampler used this pair format too, but cached
 * 19 strips/double BAT pages and sourced textures from Arcade Card RAM.
 */
#ifndef PCE_MICRO_FLOOR128_H
#define PCE_MICRO_FLOOR128_H
#include "bat_bitmap.h"
#include "pce_fastmath.h"
/* Signed five-pixel camera steps; no runtime multiply/divide. */
static const int8_t floor_step_sin[16] = {
    0,1,3,4,5,4,3,1,0,-1,-3,-4,-5,-4,-3,-1
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
__attribute__((noinline)) static void floor_draw(uint8_t angle,uint8_t cx,uint8_t cy) {
    for (uint8_t y=0; y<128u; ++y) {
        bat_bitmap_row(y);
        if (y<35u) {
            uint8_t sky=0;
            if (y>=30u) sky=6;
            else if(y>=25u) sky=5;
            else if(y>=20u) sky=4;
            else if(y>=15u) sky=3;
            else if(y>=10u) sky=2;
            else if(y>=5u) sky=1;
            for (uint8_t pair=0; pair<64; ++pair) bat_bitmap_pair(sky,sky);
        } else {
            uint8_t row=(uint8_t)(y-35u);
            int16_t cp=pce_mode7_axis((uint8_t)(angle+4u),row);
            int16_t sp=pce_mode7_axis(angle,row);
            int16_t du=pce_q6(cp);
            int16_t dv=pce_q6(sp);
            uint16_t u=(uint16_t)(((uint16_t)cx<<7)-(uint16_t)sp-((uint16_t)du<<6));
            uint16_t v=(uint16_t)(((uint16_t)cy<<7)+(uint16_t)cp-((uint16_t)dv<<6));
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
