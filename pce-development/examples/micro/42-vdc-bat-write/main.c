#include "../gfx.h"
int main(void) {
    graphics_init();
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,0);
    *IO_VDC_INDEX = VDC_REG_VRAM_DATA;
    *IO_VDC_DATA = 0x0080;
    for (;;) {}
}
