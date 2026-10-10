#include <stdint.h>
#include "calculation_result.h"
/* Debugger-visible reviewed constant from host-side Python math. */
volatile uint16_t calculated_transfer_bytes;
int main(void) {
    calculated_transfer_bytes = EXAMPLE_TRANSFER_BYTES;
    for (;;) {}
}
