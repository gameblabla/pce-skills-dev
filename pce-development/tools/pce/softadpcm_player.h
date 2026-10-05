#pragma once

#include <stdint.h>

typedef enum {
    PCE_SOFTADPCM_OK = 0,
    PCE_SOFTADPCM_INVALID_CUE = 1,
    PCE_SOFTADPCM_CHANNEL_BUSY = 2,
    PCE_SOFTADPCM_NOT_INITIALIZED = 3,
} PceSoftAdpcmResult;

typedef struct {
    uint8_t voice;          /* decoder slot 0 or 1 */
    uint8_t psg_channel;    /* PSG channel 0 through 5 */
    uint8_t sample_bank;    /* physical bank mapped through MPR6 */
    uint8_t loop;
    uint16_t sample_address; /* CPU address in $c000-$dfff */
    uint16_t sample_count;  /* exact decoded DDA sample count */
} PceSoftAdpcmCue;

/* `timer_reload` is the HuC6280 timer reload value for the chosen sample rate. */
void pce_softadpcm_init(uint8_t timer_reload);
PceSoftAdpcmResult pce_softadpcm_play(const PceSoftAdpcmCue *cue);
void pce_softadpcm_stop(uint8_t voice);
void pce_softadpcm_stop_all(void);

/* RTI entry for a raw timer vector or the CD-ROM² BIOS timer callback. */
void pce_softadpcm_irq(void);

/* RTS service for an existing IRQ wrapper. It expects decimal mode clear,
 * clobbers A/X/Y, and acknowledges no interrupt; the surrounding handler
 * owns register preservation, timer acknowledgement, and RTI. */
void pce_softadpcm_service(void);

/* The assembly state occupies 33 bytes of HuC6280 direct-page RAM. Its default
 * base is PCE_SOFTADPCM_STATE_ADDRESS (0x2080), configurable when assembling. */
extern volatile uint8_t pce_softadpcm_active;
