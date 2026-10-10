#include <pce.h>
static const uint16_t palette[16] = {
    VCE_COLOR(0,0,0), VCE_COLOR(7,0,0),
    VCE_COLOR(0,7,0), VCE_COLOR(0,0,7),
    VCE_COLOR(7,7,7)
};
int main(void) {
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vce_copy_palette(0,palette,1);
    for (;;) {}
}
