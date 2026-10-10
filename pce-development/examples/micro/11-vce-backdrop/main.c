#include <pce.h>
int main(void) {
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vce_set_color(0,VCE_COLOR(0,3,7));
    for (;;) {}
}
