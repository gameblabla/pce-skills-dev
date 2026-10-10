/* Graphics-only convenience code; never include from an audio example. */
#ifndef PCE_MICRO_GFX_H
#define PCE_MICRO_GFX_H
#include <pce.h>
/* One 8x8, 4bpp checkerboard tile at VRAM word 0x0800. */
static const uint8_t tile[32] = {
    0xaa,0x00,0x55,0x00,0xaa,0x00,0x55,0x00,
    0xaa,0x00,0x55,0x00,0xaa,0x00,0x55,0x00,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
};
static void graphics_init(void) {
    pce_vdc_bg_disable();
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);
    pce_vce_set_color(0, VCE_COLOR(0,0,1));
    pce_vce_set_color(1, VCE_COLOR(7,7,0));
    pce_vdc_copy_to_vram(0x0800,tile,sizeof(tile));
    /* The BAT is VRAM words; pattern 0x0800 / 16 = 0x80. */
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,0);
    *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
    for(uint16_t i=0;i<1024;++i) *IO_VDC_DATA=0x0080;
    pce_vdc_bg_enable();
}
#endif
