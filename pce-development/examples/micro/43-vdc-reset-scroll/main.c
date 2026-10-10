#include "../gfx.h"
int main(void) {
    graphics_init();
    pce_vdc_poke(VDC_REG_BG_SCROLL_X,32);
    pce_vdc_poke(VDC_REG_BG_SCROLL_Y,16);
    pce_vdc_poke(VDC_REG_BG_SCROLL_X,0);
    pce_vdc_poke(VDC_REG_BG_SCROLL_Y,0);
    for (;;) {}
}
