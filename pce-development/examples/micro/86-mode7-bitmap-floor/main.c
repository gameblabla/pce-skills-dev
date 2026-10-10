#include "../floor128.h"
#ifndef MODE7_START_ANGLE
#define MODE7_START_ANGLE 0
#endif

/* Software perspective into a 512x224 BAT-backed pseudo-bitmap. */
int main(void) {
    uint8_t heading=MODE7_START_ANGLE, x=64, y=0, before=0;
    floor_setup();
    floor_draw(heading,x,y);
    bat_bitmap_display();
    for (;;) {
        uint8_t keys=(uint8_t)~pce_joypad_read();
        uint8_t pressed=keys & (uint8_t)~before;
        before=keys;
        if (pressed & KEY_LEFT) --heading;
        if (pressed & KEY_RIGHT) ++heading;
        if (pressed & (KEY_UP|KEY_DOWN)) {
            int8_t move=(pressed & KEY_UP)?5:-5;
            if (move>0) {
                x-=floor_step_sin[heading&15u];
                y+=floor_step_sin[(heading+4u)&15u];
            } else {
                x+=floor_step_sin[heading&15u];
                y-=floor_step_sin[(heading+4u)&15u];
            }
        }
        if (pressed) {
            bat_bitmap_pause();
            floor_draw(heading,x,y);
            bat_bitmap_display();
        }
    }
}
