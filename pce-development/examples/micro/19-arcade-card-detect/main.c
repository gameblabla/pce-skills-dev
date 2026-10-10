#include <stdint.h>
volatile uint8_t card_present;
int main(void) {
    card_present = (*(volatile uint8_t*)0x1aff == 0x51);
    for (;;) {}
}
