#include <stdint.h>
#include "pce_fastmath.h"
volatile uint16_t quotient;
int main(void) {
    for(;;) quotient=pce_div16by8(38017u,137u);
}
