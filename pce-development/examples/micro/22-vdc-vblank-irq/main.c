#include <pce.h>
volatile uint8_t frames;
__attribute__((interrupt)) void irq_vdc(void) {
    if (*IO_VDC_STATUS & VDC_FLAG_VBLANK) ++frames;
}
int main(void) {
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_irq_vblank_enable();
    pce_irq_enable(IRQ_VDC);
    pce_cpu_irq_enable();
    for (;;) {}
}
