#include "../bat_bitmap.h"
#include "pce_fastmath.h"
/* Basic *BAT-backed* 128x128 pseudo-bitmap: no CPU framebuffer or tiles. */
int main(void) {
    static const uint16_t palette[16]={VCE_COLOR(0,0,0),VCE_COLOR(7,0,0)};
    bat_bitmap_setup(palette);
    for (uint8_t y=0; y<128; ++y) {
        bat_bitmap_row(y);
        int16_t dy=(int16_t)y-64;
        uint8_t abs_y=(uint8_t)(dy<0?-dy:dy);
        int8_t radius=pce_circle_radius(abs_y);
        for (uint8_t p=0; p<64; ++p) {
            int16_t a=(int16_t)(p<<1)-64;
            int16_t b=a+1;
            uint8_t c0=(radius>=0 && a>=-radius && a<=radius)?1u:0u;
            uint8_t c1=(radius>=0 && b>=-radius && b<=radius)?1u:0u;
            bat_bitmap_pair(c0,c1);
        }
    }
    bat_bitmap_display();
    for (;;) {}
}
