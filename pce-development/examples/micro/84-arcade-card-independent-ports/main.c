#include <stdint.h>
volatile uint8_t verified;
int main(void) {
    volatile uint8_t *a=(volatile uint8_t*)0x1a00;
    volatile uint8_t *b=(volatile uint8_t*)0x1a10;
    if(*(volatile uint8_t*)0x1aff!=0x51) for (;;) {}
    a[2]=0; a[3]=0; a[4]=1;
    b[2]=0; b[3]=0x20; b[4]=1;
    a[5]=b[5]=0; a[6]=b[6]=0;
    a[7]=b[7]=1; a[8]=b[8]=0; a[9]=b[9]=0x11;
    a[0]=0x12; b[0]=0x34;
    a[2]=0; a[3]=0; a[4]=1;
    b[2]=0; b[3]=0x20; b[4]=1;
    verified=(a[0]==0x12 && b[0]==0x34);
    for (;;) {}
}
