#include <pce.h>
#ifdef PCE_CDROM2
#include <pce/cd/bios.h>
#endif
#include <stdint.h>
#include "demo_video.h"

/* Set this sector from the disc manifest before using the read path. */
#ifdef PCE_CDROM2
static const pce_sector_t demo_file_start = {.lo = 0, .md = 0, .hi = 0};
static uint8_t cpu_stage[2048];

static uint8_t read_one_sector_to_cpu(void) {
    return pce_cdb_cd_read(demo_file_start, PCE_CDB_ADDRESS_BYTES,
                           (uint16_t)(uintptr_t)cpu_stage, sizeof(cpu_stage));
}
#else
/* The default HuCard build has no drive. It displays the no-disc result. */
static uint8_t read_one_sector_to_cpu(void) {
    return 0x0b; /* PCE_CDB_NO_DISC */
}
#define PCE_CDB_SUCCESS 0x00
#endif

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
    for (;;) {
        demo_wait_frame();
        if (demo_read_pad() & KEY_1) {
            uint8_t result = read_one_sector_to_cpu();
            /* A project loader checks this result before consuming cpu_stage. */
            demo_set_color(0, 3, result == PCE_CDB_SUCCESS
                                     ? VCE_COLOR(1, 7, 2)
                                     : VCE_COLOR(7, 1, 1));
        }
    }
}
