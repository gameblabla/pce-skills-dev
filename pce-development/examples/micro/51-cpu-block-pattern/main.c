#include <pce.h>
volatile uint8_t verified;
int main(void) {
    static const uint8_t pair[2]={0x55,0xaa};
    uint8_t dst[16]={0};
    pce_memop(dst,pair,sizeof(dst),PCE_MEMOP_ALT_INCR);
    verified=1;
    for(uint8_t i=0;i<sizeof(dst);++i) if(dst[i]!=pair[i&1]) verified=0;
    for (;;) {}
}
