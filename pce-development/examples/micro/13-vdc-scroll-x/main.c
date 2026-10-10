#include "../gfx.h"
#include "../delay.h"
int main(void) {
    graphics_init();
    for (uint16_t x=0;;++x) {
        pce_vdc_poke(VDC_REG_BG_SCROLL_X,x);
        pause_cpu(5000); /* No raster synchronization; tearing is possible. */
    }
}
