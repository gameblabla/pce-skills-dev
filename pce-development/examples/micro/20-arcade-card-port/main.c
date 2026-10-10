#include <stdint.h>
volatile uint8_t passed;
int main(void) {
    volatile uint8_t *p=(volatile uint8_t*)0x1a00;
    if (*(volatile uint8_t*)0x1aff != 0x51) for(;;) {}
    p[2]=0; p[3]=0; p[4]=1; /* address 0x010000 */
    p[5]=0; p[6]=0; p[7]=1; p[8]=0; p[9]=0x11;
    for (uint8_t i=0;i<8;++i) p[0]=i;
    p[2]=0; p[3]=0; p[4]=1; /* re-seek */
    passed=1;
    for (uint8_t i=0;i<8;++i) if(p[0]!=i) passed=0;
    for (;;) {}
}
