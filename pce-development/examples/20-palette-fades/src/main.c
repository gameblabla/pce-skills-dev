#include <pce.h>
#include "demo_video.h"

static uint16_t fade_to_black(uint16_t color, uint8_t amount) {
    uint8_t blue = color & 7;
    uint8_t red = (color >> 3) & 7;
    uint8_t green = (color >> 6) & 7;
    blue = blue > amount ? (uint8_t)(blue - amount) : 0;
    red = red > amount ? (uint8_t)(red - amount) : 0;
    green = green > amount ? (uint8_t)(green - amount) : 0;
    return VCE_COLOR(red, green, blue);
}

int main(void) {
    static const uint16_t original[16] = {
        0, VCE_COLOR(7,7,7), VCE_COLOR(7,2,1), VCE_COLOR(1,6,7),
        VCE_COLOR(7,6,1), VCE_COLOR(2,2,7), VCE_COLOR(1,7,2), VCE_COLOR(7,1,5),
        VCE_COLOR(5,5,5), VCE_COLOR(7,4,2), VCE_COLOR(2,5,7), VCE_COLOR(4,7,2),
        VCE_COLOR(5,2,7), VCE_COLOR(7,7,3), VCE_COLOR(3,6,6), VCE_COLOR(7,3,4)
    };
    uint8_t amount = 0;
    int8_t direction = 1;
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) {
        demo_wait_frame();
        for (uint8_t i = 0; i < 16; ++i)
            demo_set_color(0, i, fade_to_black(original[i], amount));
        amount = (uint8_t)(amount + direction);
        if (amount == 7) direction = -1;
        if (amount == 0) direction = 1;
    }
}
