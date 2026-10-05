#include <pce.h>
#include "demo_video.h"
#include "softadpcm_player.h"
#ifdef PCE_SOFTADPCM_CDROM2
#include "softadpcm_player_cdrom2.h"
#endif

/* Replace these deployment fields with the packed sample's actual bank manifest. */
static const PceSoftAdpcmCue project_cue = {
    .voice = 0, .psg_channel = 4, .sample_bank = 0x40, .loop = 0,
    .sample_address = 0xc000, .sample_count = 64
};

int main(void) {
    demo_video_init(320, VCE_PIXEL_CLOCK_7MHZ);
#ifdef PCE_SOFTADPCM_CDROM2
    pce_softadpcm_install_cdrom2_irq();
#endif
    pce_softadpcm_init((uint8_t)PCE_FREQ_TO_TIMER(6991));
    for (;;) {
        demo_wait_frame();
        if (demo_read_pad() & KEY_1) (void)pce_softadpcm_play(&project_cue);
        if (demo_read_pad() & KEY_2) pce_softadpcm_stop_all();
    }
}
