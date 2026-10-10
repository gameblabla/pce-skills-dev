#include <pce.h>
volatile uint8_t is_supergrafx, verified;
int main(void) {
    static const uint8_t pattern[32] = {1,2,3,4};
    uint8_t result[32];
    is_supergrafx = pce_sgx_detect();
    if (is_supergrafx) {
        pce_sgx_vdc_init();
        pce_sgx_vdc2_set();
        pce_vdc_copy_to_vram(0x0800,pattern,sizeof(pattern));
        pce_vdc_copy_from_vram(result,0x0800,sizeof(result));
        verified = 1;
        for (uint8_t i=0;i<32;++i) if (result[i]!=pattern[i]) verified=0;
        pce_sgx_vdc1_set();
    }
    for (;;) {}
}
