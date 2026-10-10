/* Fast, 8/16-bit-only arithmetic for the HuC6280. No libm, no soft mul/div. */
#ifndef PCE_LIBCOMMON_FASTMATH_H
#define PCE_LIBCOMMON_FASTMATH_H
#include <stdint.h>
/* Exact unsigned 8x8 -> 16 product. Shift/add: deterministic, no __mulhi3. */
uint16_t pce_mul8(uint8_t a, uint8_t b);
/* Exact signed 8x unsigned 8 -> signed 16; -128 supported. */
int16_t pce_mul_s8u8(int8_t a, uint8_t b);
/* Exact unsigned 16 / nonzero unsigned 8; divisor zero returns 0xffff. */
uint16_t pce_div16by8(uint16_t value, uint8_t divisor);
/* Signed right shift truncating towards zero; bits in [0,7]. */
int16_t pce_shift_towards_zero(int16_t v, uint8_t bits);
/* Hot-path exact signed /64, constant shift, not a software divisor. */
int16_t pce_q6(int16_t v);
/* No CPU divide or multiply: offline-computed (coefficient * depth) for
   a 128x128 road texture; angle wraps every 16, row 0..92. */
int16_t pce_mode7_axis(uint8_t angle, uint8_t row);
/* Pixel-perfect circle radius for |dy| <=39, or -1 outside. */
int8_t pce_circle_radius(uint8_t dy);
#endif
