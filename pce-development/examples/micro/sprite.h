/* Sprites only: one asymmetric 16x16 pattern and one SAT entry. */
#ifndef PCE_MICRO_SPRITE_H
#define PCE_MICRO_SPRITE_H
#include <pce.h>
__attribute__((interrupt)) void irq_vdc(void) {
    (void)*IO_VDC_STATUS;
}
static void sprite_init(void) {
    static uint8_t pixels[128];
    static const vdc_sprite_t blank[64]={0};
    /* Each of four bitplanes has 16 rows of two bytes. Left half lit. */
    for(uint8_t plane=0;plane<4;++plane)
        for(uint8_t row=0;row<16;++row) {
            pixels[(uint8_t)(plane*32 + row*2)]=0xff;
            pixels[(uint8_t)(plane*32 + row*2+1)]=0;
        }
    pce_vdc_sprite_disable();
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vce_set_color(0,VCE_COLOR(0,0,2));
    pce_vce_set_color(0x10f,VCE_COLOR(7,7,0));
    pce_vdc_set_copy_word();
    pce_vdc_copy_to_vram(0x6000,pixels,sizeof(pixels));
    pce_vdc_copy_to_vram(0x7f00,blank,sizeof(blank));
    pce_vdc_sprite_set_table_start(0x7f00);
    pce_vdc_poke(VDC_REG_DMA_CONTROL,VDC_DMA_REPEAT_SATB);
    pce_vdc_irq_vblank_enable();
    pce_irq_enable(IRQ_VDC);
    pce_vdc_sprite_enable();
    pce_cpu_irq_enable();
}
static void sprite_put(int16_t x,int16_t y,uint16_t attr) {
    /* Sprite pattern index is VRAM word address / 32: 0x6000 -> 0x0300. */
    const vdc_sprite_t item={(uint16_t)(y+64),
        (uint16_t)(x+32),0x0300,attr};
    pce_vdc_copy_to_vram(0x7f00,&item,sizeof(item));
}
#endif
