/* A tiny SNES Mode 7-like software floor for ordinary PC Engine HuCards.
 * 128x128 OUTPUT pixels, 4 bitplanes/16 VCE colours, no audio or CD hardware.
 * The VDC is tile-based: each projected pixel is packed into a unique 8x8
 * background pattern. No native PCE bitmap mode is assumed.
 *
 * Saber Rider's older renderer was faster: paired-colour BAT characters,
 * 19 horizontal perspective strips, Arcade Card texture and double buffering.
 * This small teaching version deliberately prioritises readable C instead.
 */
#ifndef PCE_MICRO_FLOOR128_COLOR_H
#define PCE_MICRO_FLOOR128_COLOR_H
#include <pce.h>

#define FLOOR128_W 128u
#define FLOOR128_H 128u
#define FLOOR128_PATTERN_WORD 0x0800u

/* 16 angle steps, Q7, like the 128-heading lookup idea in old floor_tables.py. */
static const int8_t floor128_sin[16] = {
    0,49,90,117,127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49
};
static const int8_t floor128_cos[16] = {
    127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49,0,49,90,117
};

/* The ground map is a repeating 128x128 four-bit colour texture.
 * Procedural pixels mean no picture converter or large C hex tables.
 * Replace this function with a packed 4bpp ROM texture lookup to use art.
 */
static uint8_t floor128_texel(uint8_t x, uint8_t y) {
    static const int8_t bends[16] = {
        0,3,6,10,12,13,11,7,2,-4,-9,-12,-11,-7,-3,0
    };
    int16_t side = (int16_t)x - (64 + bends[y >> 3]);
    uint8_t distance = (uint8_t)(side < 0 ? -side : side);
    if (distance < 20) {
        if (distance >= 16) return (y & 8) ? 11 : 12; /* red/white kerb */
        if (distance < 2 && (y & 31) < 18) return 13;  /* dashed yellow line */
        if ((y & 15) == 0) return 10;                 /* road highlight */
        return ((x ^ y) & 8) ? 9 : 8;                  /* two-tone asphalt */
    }
    if ((x & 31) < 2 && (y & 31) < 2) return 14;    /* roadside flowers */
    if (((x + (y >> 1)) & 31) == 0) return 15;
    if (((x ^ y) & 31) < 3) return 7;               /* brighter grass */
    if (((x >> 4) & 1) && ((y >> 4) & 1)) return 4;   /* darker grass */
    return ((x >> 3) ^ (y >> 3)) & 1 ? 5 : 6;         /* grass checker */
}

/* Compute affine mapping once per 8-pixel tile row, not per pixel. This
 * mirrors the crucial optimisation in the original 19-strip floor sampler.
 * Coordinates wrap at 128 texels; one step is a signed Q7 amount.
 */
typedef struct {
    uint16_t u, v;
    int16_t du, dv;
} Floor128Row;

static Floor128Row floor128_row(uint8_t y, uint8_t angle,
                                uint8_t camera_x, uint8_t camera_y) {
    Floor128Row out;
    uint16_t distance = (uint16_t)(1408u / (uint16_t)(y - 27u));
    int16_t cs = floor128_cos[angle & 15], sn = floor128_sin[angle & 15];
    out.du = (int16_t)((cs * (int16_t)distance) / 64);
    out.dv = (int16_t)((sn * (int16_t)distance) / 64);
    out.u = ((uint16_t)camera_x << 7) - (int16_t)(sn * distance) - (int16_t)(out.du * 64);
    out.v = ((uint16_t)camera_y << 7) + (int16_t)(cs * distance) - (int16_t)(out.dv * 64);
    return out;
}

static uint8_t floor128_sky(uint8_t y) {
    if (y == 34) return 3;
    if (y > 26) return 2;
    return ((y >> 3) & 1) ? 1 : 0;
}

static void floor128_setup(void) {
    static const uint16_t colors[16] = {
        VCE_COLOR(0,1,3), VCE_COLOR(0,2,5), VCE_COLOR(2,4,6), VCE_COLOR(5,6,7),
        VCE_COLOR(0,3,0), VCE_COLOR(0,4,1), VCE_COLOR(1,5,1), VCE_COLOR(2,6,2),
        VCE_COLOR(2,2,2), VCE_COLOR(3,3,3), VCE_COLOR(5,5,5), VCE_COLOR(7,1,1),
        VCE_COLOR(7,7,7), VCE_COLOR(7,7,0), VCE_COLOR(7,4,1), VCE_COLOR(2,7,6)
    };
    pce_vdc_bg_disable();
    pce_vdc_set_resolution(256, 224, VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);
    pce_vdc_set_copy_word();
    for (uint8_t c = 0; c < 16; ++c) pce_vce_set_color(c, colors[c]);
    /* 16x16 unique 8x8 patterns for the 128x128 view at (64,48). */
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR, 0);
    *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
    for (uint8_t y = 0; y < 32; ++y)
        for (uint8_t x = 0; x < 32; ++x) {
            uint16_t tile = 0x40;
            if (x >= 8 && x < 24 && y >= 6 && y < 22)
                tile = 0x80u + (uint16_t)(y - 6u) * 16u + (x - 8u);
            *IO_VDC_DATA = tile;
        }
    /* Blank character 0x40, used outside the view. */
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR, 0x0400);
    *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
    for (uint8_t i = 0; i < 16; ++i) *IO_VDC_DATA = 0;
}

/* VDC 4bpp pattern: 8 rows of interleaved plane 0/1 followed by 2/3.
 * Upload per character; no 8 KiB framebuffer consuming all PCE work RAM.
 */
static void floor128_draw(uint8_t angle, uint8_t camera_x, uint8_t camera_y) {
    uint16_t words[16];
    pce_vdc_bg_disable();            /* tearing-free demo, deliberately slow */
    for (uint8_t ty = 0; ty < 16; ++ty) {
        for (uint8_t tx = 0; tx < 16; ++tx) {
            for (uint8_t py = 0; py < 8; ++py) {
                uint8_t y = (uint8_t)(ty*8+py);
                uint8_t p0=0,p1=0,p2=0,p3=0;
                uint16_t u=0, v=0;
                int16_t du=0, dv=0;
                if (y >= 35) {
                    Floor128Row row = floor128_row(y, angle, camera_x, camera_y);
                    du = row.du; dv = row.dv;
                    /* Unsigned modular arithmetic: Q7 map wraps every 128 texels. */
                    u = row.u + (uint16_t)du * (uint16_t)(tx*8u);
                    v = row.v + (uint16_t)dv * (uint16_t)(tx*8u);
                }
                for (uint8_t px = 0; px < 8; ++px) {
                    uint8_t c = (y < 35) ? floor128_sky(y) :
                        floor128_texel((u >> 7) & 127u, (v >> 7) & 127u);
                    uint8_t mask = (uint8_t)(0x80u >> px);
                    if (c & 1) p0 |= mask;
                    if (c & 2) p1 |= mask;
                    if (c & 4) p2 |= mask;
                    if (c & 8) p3 |= mask;
                    u += du; v += dv;
                }
                words[py] = (uint16_t)p0 | ((uint16_t)p1 << 8);
                words[8+py] = (uint16_t)p2 | ((uint16_t)p3 << 8);
            }
            pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,
                    FLOOR128_PATTERN_WORD + ((uint16_t)ty*16 + tx)*16);
            *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
            for (uint8_t i = 0; i < 16; ++i) *IO_VDC_DATA = words[i];
        }
    }
    pce_vdc_bg_enable();
}
#endif
