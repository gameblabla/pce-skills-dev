#include "../gfx.h"
int main(void) {
    graphics_init();
    pce_vdc_set_copy_word();
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,32*8);
    *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
    for(uint8_t col=0;col<32;++col) *IO_VDC_DATA=0;
    for (;;) {}
}
