#include "../floor128.h"
static uint8_t texture[BITMAP128_BYTES];
static uint8_t projected[BITMAP128_BYTES];
int main(void) {
    uint8_t heading = 0, last = 0;
    bitmap128_clear(texture);
    bitmap128_circle(texture, 64, 64, 26);
    bitmap128_screen();
    floor128_project(texture, projected, heading);
    bitmap128_present(projected);
    pce_vdc_bg_enable();
    for (;;) {
        uint8_t now = (uint8_t)~pce_joypad_read();
        uint8_t pressed = now & (uint8_t)~last;
        last = now;
        if (pressed & (KEY_LEFT | KEY_RIGHT)) {
            if (pressed & KEY_LEFT) --heading;
            if (pressed & KEY_RIGHT) ++heading;
            pce_vdc_bg_disable(); /* No half-updated bitmap is shown. */
            floor128_project(texture, projected, heading);
            bitmap128_present(projected);
            pce_vdc_bg_enable();
        }
    }
}
