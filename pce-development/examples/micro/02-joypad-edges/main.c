#include <pce.h>
volatile uint8_t newly_pressed;
int main(void) {
    uint8_t old = 0;
    for (;;) {
        uint8_t now = (uint8_t)~pce_joypad_read();
        newly_pressed = now & (uint8_t)~old;
        old = now;
    }
}
