#include "../gfx.h"
#include "../delay.h"
int main(void) {
    uint16_t offset=0;
    graphics_init();
    for (;;) {
        pce_vdc_poke(VDC_REG_BG_SCROLL_X,offset);
        pce_vdc_poke(VDC_REG_BG_SCROLL_Y,offset);
        ++offset;
        pause_cpu(18000);
    }
}
