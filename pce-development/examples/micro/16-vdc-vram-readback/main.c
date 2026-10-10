#include <pce.h>
volatile uint8_t passed;
int main(void) {
    uint8_t out[32];
    static const uint8_t pattern[32] = {1,2,3,4};
    pce_vdc_set_copy_word();
    pce_vdc_copy_to_vram(0x0800,pattern,32);
    pce_vdc_copy_from_vram(out,0x0800,32);
    passed = 1;
    for(uint8_t i=0;i<32;++i) if(out[i]!=pattern[i]) passed=0;
    for (;;) {}
}
