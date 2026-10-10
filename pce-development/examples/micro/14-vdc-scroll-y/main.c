#include "../gfx.h"
#include "../delay.h"
int main(void) {
    graphics_init();
    for (uint16_t y=0;;++y) {
        pce_vdc_poke(VDC_REG_BG_SCROLL_Y,y);
        pause_cpu(5000);
    }
}
