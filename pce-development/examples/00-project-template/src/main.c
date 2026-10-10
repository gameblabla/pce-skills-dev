#include <stdint.h>
/* Minimal boot template: no graphics, input, sound, or CD initialization. */
volatile uint8_t booted;
int main(void) {
    booted = 1;
    for (;;) {}
}
