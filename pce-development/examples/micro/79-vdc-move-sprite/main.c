#include "../sprite.h"
#include "../delay.h"
int main(void) {
    sprite_init();
    for (;;) for(uint8_t x=32;x<210;x+=2) {
        sprite_put(x,104,VDC_SPRITE_FG);
        pause_cpu(18000);
    }
}
