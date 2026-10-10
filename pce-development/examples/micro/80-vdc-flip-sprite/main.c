#include "../sprite.h"
#include "../delay.h"
int main(void) {
    sprite_init();
    for (;;) {
        sprite_put(112,104,VDC_SPRITE_FG);
        pause_cpu(55000);
        sprite_put(112,104,VDC_SPRITE_FG | VDC_SPRITE_FLIP_X);
        pause_cpu(55000);
    }
}
