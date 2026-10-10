#include "../gfx.h"
int main(void) {
    graphics_init();
    pce_vdc_set_copy_column_32();
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,4);
    *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
    for(uint8_t row=0;row<28;++row) *IO_VDC_DATA=0;
    for (;;) {}
}
