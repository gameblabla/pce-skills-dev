#include <stdint.h>
volatile uint8_t verified;
int main(void) {
    volatile uint8_t *p=(volatile uint8_t*)0x1a00;
    if (*(volatile uint8_t*)0x1aff!=0x51) for (;;) {}
    p[2]=0xfc; p[3]=0xff; p[4]=1;
    p[5]=0; p[6]=0; p[7]=1; p[8]=0; p[9]=0x11;
    for(uint8_t i=0;i<8;++i) p[0]=i+1;
    p[2]=0xfc; p[3]=0xff; p[4]=1;
    verified=1;
    for(uint8_t i=0;i<8;++i) if(p[0]!=(uint8_t)(i+1)) verified=0;
    for (;;) {}
}
