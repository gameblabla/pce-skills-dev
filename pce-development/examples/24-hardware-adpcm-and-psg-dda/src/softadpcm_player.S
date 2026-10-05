/* SoftADPCM is TurboXRay's original 2-bit software ADPCM decoder.
 * This PCE runtime adaptation follows Saber Rider commit 3ade2d8.
 * Timer IRQ delivers two independent decoded streams to PSG DDA channels.
 * The decoder tables are bundled as source; no ROM is read at build time.
 * pce_softadpcm_irq is an RTI entry; pce_softadpcm_service is for an existing IRQ wrapper.
 */
.section .text.irq,"ax",@progbits
.global pce_softadpcm_irq
.global pce_softadpcm_service
#ifdef PCE_SOFTADPCM_HUCARD_IRQ
/* The HuCard ROM's native timer vector points directly at the RTI handler. */
.global irq_timer
.set irq_timer,pce_softadpcm_irq
#endif

/* HuC6280 direct-page work RAM. Override at assembly time if this range is
 * already reserved by the project; reserve all 33 bytes from C allocations. */
#ifndef PCE_SOFTADPCM_STATE_ADDRESS
#define PCE_SOFTADPCM_STATE_ADDRESS 0x2080
#endif
.global pce_softadpcm_voices,pce_softadpcm_active
pce_softadpcm_voices = PCE_SOFTADPCM_STATE_ADDRESS
pce_softadpcm_active = PCE_SOFTADPCM_STATE_ADDRESS + 32

pce_softadpcm_irq:
    pha
    phx
    phy
    stz 0x1403
    cld
    jsr pce_softadpcm_service
    ply
    plx
    pla
    rti

/* Keep this code and the six lookup tables in an always-mapped region.
 * Sample bytes are mapped temporarily through MPR6 by pce_softadpcm_decode. */
.section .text.pce_softadpcm,"ax",@progbits
.global pce_softadpcm_service
.extern pce_softadpcm_small_lo,pce_softadpcm_small_hi,pce_softadpcm_large_lo,pce_softadpcm_large_hi
.extern pce_softadpcm_next_small,pce_softadpcm_next_large

/* State offsets: left=0, read=2, predictor=4, index=6, packed=7,
 * phase=8, bank=9, loop=10, PSG channel=11, start=12, count=14.
 * Each record is 16 bytes; X selects offset 0 or 16. */
pce_softadpcm_service:
    lda pce_softadpcm_active
    and #1
    beq .Lsecond
    ldx #0
    lda pce_softadpcm_voices+11,x
    sta 0x0800
    jsr pce_softadpcm_decode
.Lsecond:
    lda pce_softadpcm_active
    and #2
    beq .Lidle_check
    ldx #16
    lda pce_softadpcm_voices+11,x
    sta 0x0800
    jsr pce_softadpcm_decode
.Lidle_check:
    lda pce_softadpcm_active
    bne .Lservice_done
    stz 0x0c01
.Lservice_done:
    rts

/* Caller guarantees an active voice. X selects its 16-byte state. */
pce_softadpcm_decode:
    lda pce_softadpcm_voices+8,x
    bne .Lpair
    /* Mapping and fetching happen once per four output samples. */
    tma #0x40
    pha
    lda pce_softadpcm_voices+9,x
    tam #0x40
    lda (pce_softadpcm_voices+2,x)
    sta pce_softadpcm_voices+7,x
    pla
    tam #0x40
    lda #4
    sta pce_softadpcm_voices+8,x
    inc pce_softadpcm_voices+2,x
    bne .Lpair
    inc pce_softadpcm_voices+3,x
.Lpair:
    ldy pce_softadpcm_voices+6,x
    lda pce_softadpcm_voices+7,x
    lsr
    bcs .Llarge_sign
    lsr
    bcs .Lsmall_sub
.Lsmall_add:
    lda pce_softadpcm_next_small,y
    sta pce_softadpcm_voices+6,x
    lda pce_softadpcm_voices+4,x
    adc pce_softadpcm_small_lo,y
    sta pce_softadpcm_voices+4,x
    lda pce_softadpcm_voices+5,x
    adc pce_softadpcm_small_hi,y
    bcc .Lstorehi
    lda #255
    sta pce_softadpcm_voices+4,x
    bra .Lstorehi
.Llarge_sign:
    lsr
    bcs .Llarge_sub
.Llarge_add:
    lda pce_softadpcm_next_large,y
    sta pce_softadpcm_voices+6,x
    lda pce_softadpcm_voices+4,x
    adc pce_softadpcm_large_lo,y
    sta pce_softadpcm_voices+4,x
    lda pce_softadpcm_voices+5,x
    adc pce_softadpcm_large_hi,y
    bcc .Lstorehi
    lda #255
    sta pce_softadpcm_voices+4,x
    bra .Lstorehi
.Lsmall_sub:
    lda pce_softadpcm_next_small,y
    sta pce_softadpcm_voices+6,x
    lda pce_softadpcm_voices+4,x
    sbc pce_softadpcm_small_lo,y
    sta pce_softadpcm_voices+4,x
    lda pce_softadpcm_voices+5,x
    sbc pce_softadpcm_small_hi,y
    bcs .Lstorehi
    lda #0
    sta pce_softadpcm_voices+4,x
    bra .Lstorehi
.Llarge_sub:
    lda pce_softadpcm_next_large,y
    sta pce_softadpcm_voices+6,x
    lda pce_softadpcm_voices+4,x
    sbc pce_softadpcm_large_lo,y
    sta pce_softadpcm_voices+4,x
    lda pce_softadpcm_voices+5,x
    sbc pce_softadpcm_large_hi,y
    bcs .Lstorehi
    lda #0
    sta pce_softadpcm_voices+4,x
    bra .Lstorehi
.Lstorehi:
    sta pce_softadpcm_voices+5,x
    /* The signed predictor's high byte maps to the PSG's 5-bit DAC range. */
    lsr
    lsr
    lsr
    sta 0x0806
    lsr pce_softadpcm_voices+7,x
    lsr pce_softadpcm_voices+7,x
    dec pce_softadpcm_voices+8,x
    lda pce_softadpcm_voices+0,x
    bne .Ldec
    dec pce_softadpcm_voices+1,x
.Ldec:
    dec pce_softadpcm_voices+0,x
    bne .Lstep_done
    lda pce_softadpcm_voices+1,x
    bne .Lstep_done
    lda pce_softadpcm_voices+10,x
    beq .Lmute
    /* Restart from the initial predictor and packed-byte boundary. */
    lda pce_softadpcm_voices+14,x
    sta pce_softadpcm_voices+0,x
    lda pce_softadpcm_voices+15,x
    sta pce_softadpcm_voices+1,x
    lda pce_softadpcm_voices+12,x
    sta pce_softadpcm_voices+2,x
    lda pce_softadpcm_voices+13,x
    sta pce_softadpcm_voices+3,x
    stz pce_softadpcm_voices+4,x
    lda #128
    sta pce_softadpcm_voices+5,x
    stz pce_softadpcm_voices+6,x
    stz pce_softadpcm_voices+8,x
    rts
.Lmute:
    ldy pce_softadpcm_voices+11,x
    sty 0x0800
    lda #16
    sta 0x0806
    stz 0x0804
    cpx #0
    bne .Lmute_second
    lda pce_softadpcm_active
    and #0xfe
    bra .Lmuted
.Lmute_second:
    lda pce_softadpcm_active
    and #0xfd
.Lmuted:
    sta pce_softadpcm_active
.Lstep_done:
    rts
