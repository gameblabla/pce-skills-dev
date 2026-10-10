#include <stdint.h>
/* No graphics are required merely to reach C main. */
volatile uint8_t booted;
int main(void) {
    booted = 1;
    for (;;) {}
}
