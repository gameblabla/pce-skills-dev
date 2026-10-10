/* No handwritten pixel arrays: the map and graphics are generated from JSON. */
#include <pce.h>
#include "level_art.h"
int main(void) {
    pce_vdc_bg_disable();
    pce_vdc_set_resolution(256, 224, VCE_PIXEL_CLOCK_5MHZ);
#if LEVEL_MAP_WIDTH == 32
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);
#elif LEVEL_MAP_WIDTH == 64
    pce_vdc_bg_set_size(VDC_BG_SIZE_64_32);
#else
    pce_vdc_bg_set_size(VDC_BG_SIZE_128_32);
#endif
    pce_vce_copy_palette(0, level_palette, 1);
    pce_vdc_copy_to_vram(LEVEL_PATTERN_WORD, level_patterns, sizeof(level_patterns));
    pce_vdc_copy_to_vram(0, level_bat, sizeof(level_bat));
    pce_vdc_poke(VDC_REG_BG_SCROLL_X, 0);
    pce_vdc_poke(VDC_REG_BG_SCROLL_Y, 0);
    pce_vdc_bg_enable();
    for (;;) { }
}
