#include "pce_fastmath.h"
uint16_t pce_mul8(uint8_t a, uint8_t b) {
    uint16_t result=0;
    uint16_t term=a;
    while (b) {
        if (b & 1u) result+=term;
        b>>=1;
        term<<=1;
    }
    return result;
}
int16_t pce_mul_s8u8(int8_t a, uint8_t b) {
    uint8_t magnitude = a<0 ? (uint8_t)(-(int16_t)a) : (uint8_t)a;
    uint16_t v=pce_mul8(magnitude,b);
    return a<0 ? -(int16_t)v : (int16_t)v;
}
uint16_t pce_div16by8(uint16_t value, uint8_t divisor) {
    uint16_t quotient=0, remainder=0;
    if(!divisor) return 0xffffu;
    for(uint8_t i=0;i<16u;++i) {
        remainder=(uint16_t)((remainder<<1)|(value>>15));
        value<<=1; quotient<<=1;
        if (remainder>=divisor) {remainder-=divisor; quotient|=1u;}
    }
    return quotient;
}
int16_t pce_shift_towards_zero(int16_t v, uint8_t bits) {
    if(bits>7u) bits=7u;
    if(bits==0u) return v;
    if(v<0) return -(int16_t)(((uint16_t)(-(v+1))+1u)>>bits);
    return (int16_t)((uint16_t)v>>bits);
}

int16_t pce_q6(int16_t v) {
    if(v<0) return -(int16_t)(((uint16_t)(-(v+1))+1u)>>6);
    return (int16_t)((uint16_t)v >> 6);
}
