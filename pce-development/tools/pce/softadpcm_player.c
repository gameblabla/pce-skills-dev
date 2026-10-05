#include "softadpcm_player.h"

#include <pce/hardware.h>
#include <pce/system.h>

typedef struct __attribute__((packed)) {
    uint16_t left, read, predictor;
    uint8_t index, packed, phase, bank, loop, channel;
    uint16_t start, count;
} PceSoftAdpcmVoice;

_Static_assert(sizeof(PceSoftAdpcmVoice) == 16, "SoftADPCM IRQ state stride changed");

extern volatile PceSoftAdpcmVoice pce_softadpcm_voices[2];
extern volatile uint8_t pce_softadpcm_active;

static uint8_t pce_softadpcm_timer_reload;
static uint8_t pce_softadpcm_initialized;

static void mute_channel(uint8_t channel) {
    *IO_PSG_CH_SELECT = channel;
    *IO_PSG_CH_SAMPLE = 16;
    *IO_PSG_CH_CONTROL = 0;
}

static void stop_timer_if_idle(void) {
    if (pce_softadpcm_active == 0) {
        *IO_TIMER_CONTROL = TIMER_OFF;
        pce_irq_disable(IRQ_TIMER);
        *IO_IRQ_ACK = 0;
    }
}

void pce_softadpcm_init(uint8_t timer_reload) {
    pce_cpu_irq_disable();
    *IO_TIMER_CONTROL = TIMER_OFF;
    pce_irq_disable(IRQ_TIMER);
    *IO_IRQ_ACK = 0;
    for (uint8_t i = 0; i != 2; ++i) {
        pce_softadpcm_voices[i].left = 0;
        pce_softadpcm_voices[i].phase = 0;
        pce_softadpcm_voices[i].loop = 0;
    }
    pce_softadpcm_active = 0;
    pce_softadpcm_timer_reload = timer_reload;
    pce_softadpcm_initialized = 1;
    pce_cpu_irq_enable();
}

PceSoftAdpcmResult pce_softadpcm_play(const PceSoftAdpcmCue *cue) {
    if (!pce_softadpcm_initialized)
        return PCE_SOFTADPCM_NOT_INITIALIZED;
    if (cue == 0 || cue->voice > 1 || cue->psg_channel > 5 ||
        cue->sample_count == 0)
        return PCE_SOFTADPCM_INVALID_CUE;

    /* Four 2-bit codes are packed in each byte. Keep the complete stream in
     * the one 8 KiB window that MPR6 maps at $c000-$dfff. */
    uint32_t packed_bytes = ((uint32_t)cue->sample_count + 3u) >> 2;
    uint32_t stream_end = (uint32_t)cue->sample_address + packed_bytes;
    if (cue->sample_address < 0xc000 || cue->sample_address >= 0xe000 ||
        stream_end > 0xe000)
        return PCE_SOFTADPCM_INVALID_CUE;

    pce_cpu_irq_disable();
    uint8_t voice_bit = (uint8_t)(1u << cue->voice);
    uint8_t other = cue->voice ^ 1;
    if ((pce_softadpcm_active & (1u << other)) != 0 &&
        pce_softadpcm_voices[other].channel == cue->psg_channel) {
        pce_cpu_irq_enable();
        return PCE_SOFTADPCM_CHANNEL_BUSY;
    }

    volatile PceSoftAdpcmVoice *v = &pce_softadpcm_voices[cue->voice];
    if ((pce_softadpcm_active & voice_bit) != 0 && v->channel != cue->psg_channel)
        mute_channel(v->channel);

    v->left = cue->sample_count;
    v->read = cue->sample_address;
    v->predictor = 0x8000;
    v->index = 0;
    v->packed = 0;
    v->phase = 0;
    v->bank = cue->sample_bank;
    v->loop = cue->loop != 0;
    v->channel = cue->psg_channel;
    v->start = cue->sample_address;
    v->count = cue->sample_count;
    pce_softadpcm_active |= voice_bit;

    *IO_PSG_VOLUME = 0xff;
    *IO_PSG_CH_SELECT = cue->psg_channel;
    *IO_PSG_CH_CONTROL = 0;
    *IO_PSG_CH_VOLUME = 0xff;
    *IO_PSG_CH_CONTROL = 0xdf;
    *IO_PSG_CH_SAMPLE = 16;

    if ((*IO_TIMER_CONTROL & TIMER_ON) == 0) {
        *IO_TIMER_COUNTER = pce_softadpcm_timer_reload;
        *IO_IRQ_ACK = 0;
        pce_irq_enable(IRQ_TIMER);
        *IO_TIMER_CONTROL = TIMER_ON;
    }
    pce_cpu_irq_enable();
    return PCE_SOFTADPCM_OK;
}

void pce_softadpcm_stop(uint8_t voice) {
    if (voice > 1)
        return;
    pce_cpu_irq_disable();
    uint8_t voice_bit = (uint8_t)(1u << voice);
    if ((pce_softadpcm_active & voice_bit) != 0) {
        mute_channel(pce_softadpcm_voices[voice].channel);
        pce_softadpcm_voices[voice].left = 0;
        pce_softadpcm_voices[voice].loop = 0;
        pce_softadpcm_active &= (uint8_t)~voice_bit;
    }
    stop_timer_if_idle();
    pce_cpu_irq_enable();
}

void pce_softadpcm_stop_all(void) {
    pce_cpu_irq_disable();
    for (uint8_t i = 0; i != 2; ++i) {
        if ((pce_softadpcm_active & (1u << i)) != 0)
            mute_channel(pce_softadpcm_voices[i].channel);
        pce_softadpcm_voices[i].left = 0;
        pce_softadpcm_voices[i].loop = 0;
    }
    pce_softadpcm_active = 0;
    stop_timer_if_idle();
    pce_cpu_irq_enable();
}
