#include <pce.h>
volatile uint16_t readback;
int main(void) {
    pce_vce_set_color(1,VCE_COLOR(7,3,1));
    readback = pce_vce_get_color(1);
    for (;;) {}
}
