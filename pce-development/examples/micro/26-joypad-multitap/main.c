#include <pce.h>
volatile uint8_t player1, player2;
int main(void) {
    for (;;) {
        player1 = (uint8_t)~pce_joypad_read();
        player2 = (uint8_t)~pce_joypad_next();
    }
}
