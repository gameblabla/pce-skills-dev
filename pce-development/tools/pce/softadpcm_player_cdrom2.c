#include "softadpcm_player.h"
#include "softadpcm_player_cdrom2.h"

#include <pce/cd/bios.h>

void pce_softadpcm_install_cdrom2_irq(void) {
    pce_cdb_irq_set(PCE_CDB_ID_IRQ_TIMER, pce_softadpcm_irq);
    pce_cdb_irq_enable(PCE_CDB_MASK_IRQ_TIMER);
}
