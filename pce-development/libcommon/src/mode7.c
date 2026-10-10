#include "pce_fastmath.h"
#include "mode7_lut.h"
/* Signed coefficient index for 16 orientations; cos=sin(angle+4). */
static const int8_t angle_coeff[16] = {
    0,1,2,3,4,3,2,1,0,-1,-2,-3,-4,-3,-2,-1
};
int16_t pce_mode7_axis(uint8_t angle, uint8_t row) {
    int8_t c=angle_coeff[angle&15u];
    const uint16_t *table;
    if(row>=93u) return 0;
    switch(c<0 ? -c:c) {
        case 0: table=pce_m7_lut_0; break;
        case 1: table=pce_m7_lut_1; break;
        case 2: table=pce_m7_lut_2; break;
        case 3: table=pce_m7_lut_3; break;
        default:table=pce_m7_lut_4; break;
    }
    uint16_t product=table[row];
    return c<0 ? -(int16_t)product : (int16_t)product;
}
