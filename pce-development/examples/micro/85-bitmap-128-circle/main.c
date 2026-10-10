#include "../bitmap128.h"
static uint8_t pixels[BITMAP128_BYTES];
int main(void) {
    bitmap128_clear(pixels);
    bitmap128_circle(pixels, 64, 64, 40);
    bitmap128_screen();
    bitmap128_present(pixels);
    pce_vdc_bg_enable();
    for (;;) {}
}
