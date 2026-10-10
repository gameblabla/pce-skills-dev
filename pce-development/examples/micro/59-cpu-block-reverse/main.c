#include <pce.h>
volatile uint8_t verified;
int main(void) {
    static const uint8_t src[6]={1,2,3,4,5,6};
    uint8_t dst[6]={0};
    pce_memop(&dst[5],&src[5],6,PCE_MEMOP_DECR_DECR);
    verified=1;
    for(uint8_t i=0;i<6;++i) if(src[i]!=dst[i]) verified=0;
    for (;;) {}
}
