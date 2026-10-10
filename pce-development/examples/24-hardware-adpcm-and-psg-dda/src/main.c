#include <pce.h>
#include "softadpcm_player.h"
#ifdef PCE_SOFTADPCM_CDROM2
#include "softadpcm_player_cdrom2.h"
#endif

/* Template only: these fields MUST be replaced after packaging sample data.
 * Loading sample_bank=0x40 is not provided by this HuCard example. */
static const PceSoftAdpcmCue sample_cue = {
    .voice=0, .psg_channel=4, .sample_bank=0x40, .loop=0,
    .sample_address=0xc000, .sample_count=64
};
volatile uint8_t sample_ready; /* Set to 1 after provisioning a real bank. */
volatile PceSoftAdpcmResult last_play_result;

int main(void) {
    uint8_t old = 0;
#ifdef PCE_SOFTADPCM_CDROM2
    pce_softadpcm_install_cdrom2_irq();
#endif
    pce_softadpcm_init((uint8_t)PCE_FREQ_TO_TIMER(6991));
    for (;;) {
        uint8_t now = (uint8_t)~pce_joypad_read();
        uint8_t pressed = now & (uint8_t)~old;
        if ((pressed & KEY_1) && sample_ready)
            last_play_result = pce_softadpcm_play(&sample_cue);
        if (pressed & KEY_2) pce_softadpcm_stop_all();
        old = now;
    }
}
