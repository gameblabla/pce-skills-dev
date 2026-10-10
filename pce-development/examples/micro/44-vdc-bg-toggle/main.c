#include "../gfx.h"
#include "../delay.h"
int main(void) {
    graphics_init();
    for (;;) {
        pce_vdc_bg_disable();
        pause_cpu(50000);
        pce_vdc_bg_enable();
        pause_cpu(50000);
    }
}
