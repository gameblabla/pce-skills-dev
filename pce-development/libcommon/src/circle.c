#include "pce_fastmath.h"
#include "circle_lut.h"
int8_t pce_circle_radius(uint8_t dy) {
    return dy<40u ? (int8_t)pce_circle_extent[dy] : -1;
}
