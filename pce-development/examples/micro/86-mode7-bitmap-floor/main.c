#include "../floor128.h"
#ifndef MODE7_START_ANGLE
#define MODE7_START_ANGLE 0
#endif

/* A textured racing ground, not a transformed circle. 16 colours, 128x128. */
int main(void) {
    uint8_t heading = MODE7_START_ANGLE, cam_x = 64, cam_y = 0, before = 0;
    floor128_setup();
    floor128_draw(heading, cam_x, cam_y);
    for (;;) {
        uint8_t keys = (uint8_t)~pce_joypad_read();
        uint8_t pressed = keys & (uint8_t)~before;
        before = keys;
        if (pressed & KEY_LEFT) --heading;
        if (pressed & KEY_RIGHT) ++heading;
        if (pressed & (KEY_UP | KEY_DOWN)) {
            int8_t move = (pressed & KEY_UP) ? 5 : -5;
            cam_x -= (int16_t)(floor128_sin[heading & 15] * move) / 127;
            cam_y += (int16_t)(floor128_cos[heading & 15] * move) / 127;
        }
        if (pressed) floor128_draw(heading, cam_x, cam_y);
    }
}
