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
            x-=(int16_t)(floor_sin[heading&15]*move)/127;
            y+=(int16_t)(floor_cos[heading&15]*move)/127;
        }
        if (pressed) {
            bat_bitmap_pause();
            floor_draw(heading,x,y);
            bat_bitmap_display();
        }
    }
}
