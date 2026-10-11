/* PCEdev's actual pseudo-bitmap technique, NOT planar-framebuffer uploading.
 * VDC 512x224 / 10.7 MHz; 64 visible BAT words each encode TWO four-bit
 * pixels. The tile set is fixed: 256 eight-high tiles, (left<<4)|right.
 *
 * The 128x64 BAT is read as two 64x64 halves: screen raster IRQs select
 * BXR=0/512 and BYR=row*8. Together this is 64x128 BAT words = 128x128
 * addressable pixels in VRAM, with no CPU-side framebuffer or tile conversion.
 * Logical lines are stretched to 224 physical lines by raster remapping.
 * Draw with display / VDC interrupts off (the VDC index is shared).
 */
#ifndef PCE_MICRO_BAT_BITMAP_H
#define PCE_MICRO_BAT_BITMAP_H
#include <pce.h>

#define BAT_BITMAP_W 128u
#define BAT_BITMAP_H 128u
#define BAT_BITMAP_TILE_WORD 0x2000u
#define BAT_BITMAP_TILE_BASE (BAT_BITMAP_TILE_WORD / 16u)

volatile uint8_t bat_line, bat_source_y, bat_phase, bat_frames;
#ifdef BAT_BITMAP_DOUBLE_BUFFER
/* Two independent 64x64 BAT half-pages, selected by BXR during VBlank.
 * $ff means no page is ready; the raster IRQ is the ONLY page presenter. */
volatile uint8_t bat_display_page, bat_ready_page;
#endif

/* The native tile-set has 256 entries, indexed by (left<<4)|right.
 * In full-detail mode, use a 3+2+3 horizontal transition rather than hard
 * 4+4 color slabs: PCEdev-inspired subpixel blending, with no extra BAT
 * writes or dynamic planar tile updates. Atomic/reference retain 4+4. */
static void bat_bitmap_patterns(void) {
    for (uint16_t pair=0; pair<256; ++pair) {
        uint8_t a = (uint8_t)(pair >> 4), b = (uint8_t)(pair & 15);
        uint16_t planes[4];
        uint8_t mask=1u;
        for (uint8_t bit=0; bit<4; ++bit) {
#if !RAY_DOUBLE_BUFFER && !defined(RAY_NO_SUBPIXEL_BLEND)
            uint8_t mid=ray_palette_blend_packed[pair>>1];
            mid=(uint8_t)((pair&1u)?(mid&15u):(mid>>4));
            planes[bit] = ((a & mask) ? 0xe0u : 0u) |
                          ((mid & mask) ? 0x18u : 0u) |
                          ((b & mask) ? 0x07u : 0u);
#else
            planes[bit] = ((a & mask) ? 0xf0u : 0u) |
                          ((b & mask) ? 0x0fu : 0u);
#endif
            mask=(uint8_t)(mask<<1);
        }
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,
                     (uint16_t)(BAT_BITMAP_TILE_WORD + pair*16u));
        *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
        for (uint8_t i=0; i<8; ++i)
            *IO_VDC_DATA = planes[0] | (planes[1]<<8);
        for (uint8_t i=0; i<8; ++i)
            *IO_VDC_DATA = planes[2] | (planes[3]<<8);
    }
}

static void bat_bitmap_setup(const uint16_t colors[16]) {
    pce_cpu_irq_disable();
    pce_vdc_bg_disable();
    pce_vdc_set_resolution(512,224,VCE_PIXEL_CLOCK_10MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_128_64);
    pce_vdc_set_copy_word();
    /* Colour zero is transparent on BG tiles: the backdrop supplies it.
     * Match the backdrop to this example's palette entry zero. */
    pce_vce_set_color(0, colors[0]);
    for (uint8_t i=0; i<16; ++i) pce_vce_set_color(240u+i, colors[i]);
#ifdef BAT_BITMAP_DOUBLE_BUFFER
    bat_display_page=0u;
    bat_ready_page=0xffu;
#endif
    bat_bitmap_patterns();
    /* Entire pseudo-bitmap BAT starts at VRAM $0000; use palette 15. */
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,0);
    *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
    for (uint16_t i=0; i<8192; ++i) *IO_VDC_DATA = 0xf200;
}

/* Sequential 64-word BAT row: no planar conversion, no framebuffer. */
static __attribute__((unused)) void bat_bitmap_row(uint8_t y) {
    uint16_t addr = ((uint16_t)(y & 63u)<<7) + ((y & 64u)?64u:0u);
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,addr);
    *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
}
static __attribute__((unused)) void bat_bitmap_pair(uint8_t left, uint8_t right) {
    *IO_VDC_DATA = (uint16_t)(0xf200u | ((uint16_t)(left&15u)<<4) | (right&15u));
}

/* Raster remap: the display is 512x224, but the visible 64 BAT columns
 * become 128 pixels across, and the *two halves* of 128x64 BAT are arranged
 * as 128 logical scanlines. Each virtual row is (roughly) 7/4 scanlines high.
 * Writes inside the IRQ take effect on the following scanline.
 */
#ifndef BAT_BITMAP_NATIVE_IRQ
__attribute__((interrupt)) void irq_vdc(void) {
    uint8_t status = *IO_VDC_STATUS;
    if (status & VDC_FLAG_VBLANK) {
        ++bat_frames;
        bat_line=0; bat_source_y=0; bat_phase=0;
        *IO_VDC_INDEX=VDC_REG_BG_SCROLL_X; *IO_VDC_DATA=0;
        *IO_VDC_INDEX=VDC_REG_BG_SCROLL_Y; *IO_VDC_DATA=0;
        *IO_VDC_INDEX=VDC_REG_SCANLINE; *IO_VDC_DATA=0x40;
    }
    if (status & VDC_FLAG_SCANLINE) {
        uint8_t line=bat_line;
        if (line<223u) {
            ++line; bat_line=line;
            uint8_t phase=(uint8_t)(bat_phase+4u);
            if (phase>=7u) {phase-=7u; ++bat_source_y;}
            bat_phase=phase;
            uint8_t y=bat_source_y;
            /* BXR changes only at the boundary between the two 64-row
             * BAT pages. Writing it on all 223 raster events wastes VDC
             * bus cycles and IRQ time. VBlank already restores BXR=0. */
            if (y==64u) {
                *IO_VDC_INDEX=VDC_REG_BG_SCROLL_X;
                *IO_VDC_DATA=512u;
            }
            *IO_VDC_INDEX=VDC_REG_BG_SCROLL_Y;
            /* Background Y auto-advances at line end: compensate for it. */
            *IO_VDC_DATA=(uint16_t)((((uint16_t)(y & 63u))<<3)-1u);
            *IO_VDC_INDEX=VDC_REG_SCANLINE;
            *IO_VDC_DATA=(uint16_t)(0x41u+line);
        }
    }
}

#else
extern void irq_vdc(void);
#endif

static void bat_bitmap_display(void) {
    bat_line=bat_source_y=bat_phase=0;
    pce_vdc_poke(VDC_REG_BG_SCROLL_X,0);
    pce_vdc_poke(VDC_REG_BG_SCROLL_Y,0);
    pce_vdc_poke(VDC_REG_SCANLINE,0x40);
    pce_vdc_poke(VDC_REG_CONTROL,
                 VDC_CONTROL_ENABLE_BG|VDC_CONTROL_IRQ_SCANLINE|
                 VDC_CONTROL_IRQ_VBLANK);
    pce_irq_enable(IRQ_VDC);
    pce_cpu_irq_enable();
}
static __attribute__((unused)) inline void bat_bitmap_pause(void) {
    pce_cpu_irq_disable();
    pce_vdc_poke(VDC_REG_CONTROL,0);
}
#endif
