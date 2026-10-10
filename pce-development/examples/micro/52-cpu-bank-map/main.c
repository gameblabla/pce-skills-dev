#include <pce.h>
volatile uint8_t mapped_bank;
int main(void) {
    mapped_bank = pce_bank3_get();
    for (;;) {}
}
