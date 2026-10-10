#include <pce.h>
volatile uint8_t is_supergrafx;
int main(void) {
    is_supergrafx = pce_sgx_detect();
    for (;;) {}
}
