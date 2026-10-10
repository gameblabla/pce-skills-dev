#include <stdint.h>
#include "pce_fastmath.h"
volatile int16_t horizontal;
volatile int16_t vertical;
int main(void) {
    uint8_t angle=0;
    for(;;) {
        horizontal=pce_mode7_axis(angle,12u);
        vertical=pce_mode7_axis((uint8_t)(angle+4u),12u);
        ++angle;
    }
}
