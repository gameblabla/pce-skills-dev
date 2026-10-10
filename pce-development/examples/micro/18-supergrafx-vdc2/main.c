#include <pce.h>
volatile uint8_t is_supergrafx;
int main(void) {
    is_supergrafx = pce_sgx_detect();
    if (is_supergrafx) {
        pce_sgx_vdc_init();
        pce_sgx_vdc2_set();
        pce_vdc_bg_disable();
        pce_sgx_vdc1_set();
    }
    for (;;) {}
}
