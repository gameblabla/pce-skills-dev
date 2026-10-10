#include "../gfx.h"
#include "../delay.h"
int main(void) {
    graphics_init();
    for (;;) {
        for(uint8_t red=0;red<8;++red) {
            pce_vce_set_color(1,VCE_COLOR(red,0,7));
            pause_cpu(30000);
        }
    }
}
