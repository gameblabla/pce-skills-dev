#include <pce.h>
volatile uint8_t first, second, verified;
int main(void) {
    static const uint8_t source[6]={1,2,3,4,5,6};
    uint8_t pair[2]={0};
    pce_memop(pair,source,6,PCE_MEMOP_INCR_ALT);
    first=pair[0]; second=pair[1];
    verified=(first==5 && second==6);
    for (;;) {}
}
