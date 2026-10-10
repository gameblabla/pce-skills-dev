#include "../gfx.h"
int main(void) {
    graphics_init();
    pce_vdc_set_copy_word();
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,0);
    *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
    for(uint8_t i=0;i<32;++i) *IO_VDC_DATA=(i&1)?0x0080:0;
    for (;;) {}
}
