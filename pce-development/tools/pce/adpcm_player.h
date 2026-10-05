#pragma once

#include <pce/cd/bios.h>
#include <stdint.h>

/* CD-resident sample description for the BIOS hardware ADPCM voice. */
typedef struct {
    pce_sector_t sector;
    uint16_t adpcm_address;
    uint16_t byte_length;
    uint8_t sector_count;
    uint8_t divider;
    uint8_t priority;
} PceAdpcmCue;

/* Call from the main loop, not an IRQ. The CD BIOS read may block. */
uint8_t pce_adpcm_player_start(const PceAdpcmCue *cue);
void pce_adpcm_player_stop(void);
