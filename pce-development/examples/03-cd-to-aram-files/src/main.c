#include <pce.h>
#ifdef PCE_CDROM2
#include <pce/cd/bios.h>
#endif

/* Debugger-visible status; no palette/screenshot is needed for a CD read. */
volatile uint8_t last_cd_result = 0xff;
#ifdef PCE_CDROM2
/* Replace sector zero with the file's sector from your packed-disc manifest. */
static const pce_sector_t first_sector = {.lo=0,.md=0,.hi=0};
static uint8_t sector_buffer[2048];
static uint8_t read_sector(void) {
    return pce_cdb_cd_read(first_sector,PCE_CDB_ADDRESS_BYTES,
                           (uint16_t)(uintptr_t)sector_buffer,sizeof(sector_buffer));
}
#else
static uint8_t read_sector(void) { return 0x0b; } /* no drive on HuCard */
#endif

int main(void) {
    uint8_t last = 0;
    for (;;) {
        uint8_t held = (uint8_t)~pce_joypad_read();
        if ((held & KEY_1) && !(last & KEY_1))
            last_cd_result = read_sector();
        last = held;
    }
}
