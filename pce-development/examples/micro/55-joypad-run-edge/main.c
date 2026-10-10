#include <pce.h>
volatile uint8_t started;
int main(void) {
    uint8_t before=0;
    for (;;) {
        uint8_t now=(uint8_t)~pce_joypad_read();
        if ((now & KEY_RUN) && !(before & KEY_RUN)) ++started;
        before=now;
    }
}
