#include <stdint.h>
volatile uint8_t counter;
int main(void) {
    for (;;) ++counter; /* Inspect this variable in a debugger. */
}
