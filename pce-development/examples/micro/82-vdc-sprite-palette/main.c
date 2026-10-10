#include "../sprite.h"
#include "../delay.h"
int main(void) {
    sprite_init();
    sprite_put(112,104,VDC_SPRITE_FG);
    for (;;) {
        pce_vce_set_color(0x10f,VCE_COLOR(7,0,0));
        pause_cpu(55000);
        pce_vce_set_color(0x10f,VCE_COLOR(0,7,0));
        pause_cpu(55000);
    }
}
