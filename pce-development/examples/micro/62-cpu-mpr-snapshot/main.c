#include <pce.h>
volatile uint8_t banks[3];
int main(void) {
    banks[0]=pce_bank2_get();
    banks[1]=pce_bank3_get();
    banks[2]=pce_bank4_get();
    for (;;) {}
}
