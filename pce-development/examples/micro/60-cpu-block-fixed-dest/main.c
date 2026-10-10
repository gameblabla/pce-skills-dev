#include <pce.h>
volatile uint8_t last;
int main(void) {
    static const uint8_t source[4]={10,20,30,40};
    pce_memop((void*)&last,source,4,PCE_MEMOP_INCR_NONE);
    for (;;) {}
}
