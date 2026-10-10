#include <pce.h>
volatile uint8_t directions;
int main(void) {
    for (;;) {
        directions=(uint8_t)~pce_joypad_read() &
            (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT);
    }
}
