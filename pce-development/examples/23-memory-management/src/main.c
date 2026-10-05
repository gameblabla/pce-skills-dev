#include <pce.h>
#include "demo_video.h"

typedef union {
    uint8_t scene_decode[1024];
    uint8_t audio_staging[1024];
} SequentialScratch;

static SequentialScratch scratch;
static uint8_t collision_cache[128];
static uint8_t frame_sat[64];

int main(void) {
    scratch.scene_decode[0] = 1;
    collision_cache[0] = scratch.scene_decode[0];
    frame_sat[0] = collision_cache[0];
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) demo_wait_frame();
}
