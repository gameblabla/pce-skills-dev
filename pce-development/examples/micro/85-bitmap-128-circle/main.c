#include "../bat_bitmap.h"
/* Basic *BAT-backed* 128x128 pseudo-bitmap: no CPU framebuffer or tiles. */
int main(void) {
    static const uint16_t palette[16]={VCE_COLOR(0,0,0),VCE_COLOR(7,0,0)};
    bat_bitmap_setup(palette);
    for (uint8_t y=0; y<128; ++y) {
        bat_bitmap_row(y);
        int16_t dy=(int16_t)y-64;
        for (uint8_t p=0; p<64; ++p) {
            int16_t a=(int16_t)(p*2u)-64;
            int16_t b=a+1;
            uint8_t c0=((a*a+dy*dy)<1600)?1u:0u;
            uint8_t c1=((b*b+dy*dy)<1600)?1u:0u;
            bat_bitmap_pair(c0,c1);
        }
    }
    bat_bitmap_display();
    for (;;) {}
}
