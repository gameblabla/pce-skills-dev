#include <pce.h>
volatile uint16_t scroll_x;
int main(void) {
    pce_vdc_poke(VDC_REG_BG_SCROLL_X,42);
    scroll_x = pce_vdc_peek(VDC_REG_BG_SCROLL_X);
    for (;;) {}
}
