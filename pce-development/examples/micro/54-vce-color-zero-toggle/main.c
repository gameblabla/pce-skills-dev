#include <pce.h>
#include "../delay.h"
int main(void) {
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    for (;;) {
        pce_vce_set_color(0,VCE_COLOR(7,0,0));
        pause_cpu(50000);
        pce_vce_set_color(0,VCE_COLOR(0,0,7));
        pause_cpu(50000);
    }
}
