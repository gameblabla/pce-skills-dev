#include <pce.h>
#include "demo_video.h"
#include "demo_assets.h"

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
    uint8_t amount = 0;
    uint8_t ticks = 0;
    int8_t direction = 1;
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) {
        demo_wait_frame();
        if (++ticks < 32) continue;
        ticks = 0;
        for (uint8_t i = 0; i < 16; ++i)
            demo_set_color(0, i, fade_to_black(pce_demo_palette[i], amount));
        amount = (uint8_t)(amount + direction);
        if (amount == 7) direction = -1;
        if (amount == 0) direction = 1;
    }
}
