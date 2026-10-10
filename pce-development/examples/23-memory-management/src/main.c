#include <stdint.h>
/* Two mutually exclusive phase buffers overlay the same RAM. */
typedef union {
    uint8_t scene_decode[1024];
    uint8_t audio_staging[1024];
} SequentialScratch;
static SequentialScratch scratch;
static uint8_t collision_cache[128];
static uint8_t frame_sat[64];
volatile uint8_t observed;
int main(void) {
    scratch.scene_decode[0] = 1;
    collision_cache[0] = scratch.scene_decode[0];
    frame_sat[0] = collision_cache[0];
    observed = frame_sat[0]; /* Debugger reads this, not the palette. */
    for (;;) {}
}
