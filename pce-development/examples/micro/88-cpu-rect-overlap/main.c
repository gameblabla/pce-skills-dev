#include <stdint.h>
volatile uint8_t overlap;
static uint8_t intersects(int16_t ax,int16_t ay,int16_t aw,int16_t ah,
                          int16_t bx,int16_t by,int16_t bw,int16_t bh) {
    return ax < bx+bw && ax+aw > bx && ay < by+bh && ay+ah > by;
}
int main(void) {
    for(;;)overlap=intersects(4,20,10,15,12,30,16,8);
}
