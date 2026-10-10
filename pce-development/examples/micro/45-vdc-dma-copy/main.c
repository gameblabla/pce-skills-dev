#include <pce.h>
volatile uint8_t copied;
int main(void) {
    static const uint8_t pattern[32] = {1,2,3,4};
    uint8_t result[32];
    pce_vdc_set_copy_word();
    pce_vdc_copy_to_vram(0x0800,pattern,sizeof(pattern));
    pce_vdc_dma_start(0,0x0800,0x0820,32);
    while (!pce_vdc_dma_finished()) {}
    pce_vdc_copy_from_vram(result,0x0820,sizeof(result));
    copied = 1;
    for (uint8_t i=0;i<32;++i) if (result[i]!=pattern[i]) copied=0;
    for (;;) {}
}
