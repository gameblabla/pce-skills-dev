#include <pce.h>
volatile uint8_t buttons;
int main(void) {
    for (;;) buttons = (uint8_t)~pce_joypad_read();
}
