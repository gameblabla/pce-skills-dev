#include <pce.h>
volatile uint8_t released;
int main(void) {
    uint8_t old = 0;
    for (;;) {
        uint8_t now = (uint8_t)~pce_joypad_read();
        released = old & (uint8_t)~now;
        old = now;
    }
}
