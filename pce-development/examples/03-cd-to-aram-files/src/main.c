#include <pce.h>
#include <pce/cd/bios.h>
#include <stdint.h>
#include "demo_video.h"

/* Set this sector from the disc manifest before using the read path. */
static const pce_sector_t demo_file_start = {.lo = 0, .md = 0, .hi = 0};
static uint8_t cpu_stage[2048];

static uint8_t read_one_sector_to_cpu(void) {
    return pce_cdb_cd_read(demo_file_start, PCE_CDB_ADDRESS_BYTES,
                           (uint16_t)(uintptr_t)cpu_stage, sizeof(cpu_stage));
}

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) {
        demo_wait_frame();
        if (pce_joypad_read() & KEY_1) {
            uint8_t result = read_one_sector_to_cpu();
            /* A project loader checks this result before consuming cpu_stage. */
            demo_set_color(0, 1, result == PCE_CDB_SUCCESS
                                     ? VCE_COLOR(1, 7, 2)
                                     : VCE_COLOR(7, 1, 1));
        }
    }
}
