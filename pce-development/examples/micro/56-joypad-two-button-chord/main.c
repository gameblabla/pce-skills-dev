#include <pce.h>
volatile uint8_t both;
int main(void) {
    for (;;) {
        uint8_t keys=(uint8_t)~pce_joypad_read();
        both=(keys & (KEY_1 | KEY_2)) == (KEY_1 | KEY_2);
    }
}
