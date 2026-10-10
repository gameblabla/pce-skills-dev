#include <pce.h>
volatile uint8_t verified;
int main(void) {
    static const uint8_t src[8]={1,2,3,4,5,6,7,8};
    uint8_t dst[8]={0};
    pce_memop(dst,src,sizeof(src),PCE_MEMOP_INCR_INCR);
    verified=1;
    for(uint8_t i=0;i<sizeof(src);++i) if(dst[i]!=src[i]) verified=0;
    for (;;) {}
}
