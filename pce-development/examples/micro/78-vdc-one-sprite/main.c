#include "../sprite.h"
int main(void) {
    sprite_init();
    sprite_put(112,104,VDC_SPRITE_FG);
    for (;;) {}
}
