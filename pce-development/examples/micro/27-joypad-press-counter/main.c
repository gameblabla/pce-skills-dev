#include <pce.h>
volatile uint16_t presses;
int main(void) {
    uint8_t old = 0;
    for (;;) {
        uint8_t now = (uint8_t)~pce_joypad_read();
        if ((now & KEY_1) && !(old & KEY_1)) ++presses;
        old = now;
    }
}
