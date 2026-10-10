#include <stdint.h>
#include "pce_fastmath.h"
volatile int16_t result;
int main(void) {
    for(;;) result=pce_mul_s8u8(-123,201u);
}
