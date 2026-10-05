#include "adpcm_player.h"

#include <stdbool.h>

static bool player_started;
static uint8_t player_priority;

uint8_t pce_adpcm_player_start(const PceAdpcmCue *cue) {
    if (cue == 0 || cue->sector_count == 0 || cue->byte_length == 0)
        return PCE_CDB_INVALID_PARAMETER;

    if (player_started &&
        (pce_cdb_adpcm_status() & ADPCM_STOPPED) == 0 &&
        cue->priority < player_priority)
        return PCE_CDB_NOT_READY;

    pce_cdb_adpcm_stop();
    player_started = false;
    pce_cdb_adpcm_reset();

    uint8_t result = pce_cdb_adpcm_read_from_cd(
        cue->sector, cue->sector_count, cue->adpcm_address);
    if (result != PCE_CDB_SUCCESS)
        return result;

    result = pce_cdb_adpcm_play(cue->adpcm_address, cue->byte_length,
                                cue->divider, PCE_CDB_ADPCM_ONE_SHOT);
    if (result == PCE_CDB_SUCCESS) {
        player_priority = cue->priority;
        player_started = true;
    }
    return result;
}

void pce_adpcm_player_stop(void) {
    pce_cdb_adpcm_stop();
    player_started = false;
}
