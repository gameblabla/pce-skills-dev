#include <pce.h>
volatile uint16_t polls_held;
int main(void) {
    for (;;) {
        if ((uint8_t)~pce_joypad_read() & KEY_LEFT) ++polls_held;
        else polls_held=0;
    }
}
