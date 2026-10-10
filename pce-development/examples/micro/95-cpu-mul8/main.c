#include <stdint.h>
#include "pce_fastmath.h"
volatile uint16_t result;
int main(void) {
    for(;;) result=pce_mul8(73u,129u);
}
