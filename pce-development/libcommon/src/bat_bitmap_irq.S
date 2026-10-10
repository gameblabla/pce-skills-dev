/* Native HuC6280 raster IRQ for the 512x224 BAT pseudo-bitmap.
 * Replaces the compiler-generated interrupt prologue and volatile VDC
 * register writes with direct ST0/ST1/ST2. Preserve A/X/Y and RTI.
 * Default: 128 source rows expanded to 224 CRT lines (+4/7 phase),
 * switching BXR at row 64. Optional ATOMIC: two disjoint 64-row
 * half-pages, each expanded to 224 scanlines (+2/7 phase), BXR flipped
 * only in VBlank after all back-page BAT words have been written.
 */
.section .text.irq_vdc,"ax",@progbits
.global irq_vdc
.type irq_vdc,@function
.extern bat_frames,bat_line,bat_source_y,bat_phase
#if defined(BAT_BITMAP_DOUBLE_BUFFER)
.extern bat_display_page,bat_ready_page,ray_redraws
#endif
irq_vdc:
    pha
    phx
    phy
    cld
    lda $0000                   /* acknowledge VDC interrupt, read status */
    pha
    and #$20                    /* VBlank */
    beq .Lraster_check
    inc bat_frames
    stz bat_line
    stz bat_source_y
    stz bat_phase
#if defined(BAT_BITMAP_DOUBLE_BUFFER)
    /* Atomically publish a completely written back BAT at VBlank.
     * Front is NEVER modified between presentation events. */
    lda bat_ready_page
    cmp #$ff
    beq .Lno_pending_page
    sta bat_display_page
    lda #$ff
    sta bat_ready_page
    inc ray_redraws
    bne .Lno_pending_page
    inc ray_redraws+1
.Lno_pending_page:
    st0 #7
    st1 #0
    lda bat_display_page
    beq .Lfront_left
    st2 #2                  /* BXR=512 = second BAT half */
    bra .Lfront_set
.Lfront_left:
    st2 #0
.Lfront_set:
#else
    st0 #7                       /* BXR=0 */
    st1 #0
    st2 #0
#endif
    st0 #8                       /* BYR=0 */
    st1 #0
    st2 #0
    st0 #6                       /* RCR=0x40 */
    st1 #$40
    st2 #0
.Lraster_check:
    pla
    and #$04                    /* raster */
    beq .Ldone
    lda bat_line
    cmp #223
    bcs .Ldone
    inc bat_line
    lda bat_phase
    clc
#if defined(BAT_BITMAP_DOUBLE_BUFFER)
    adc #2                  /* 64 logical lines per 224 physical lines */
#else
    adc #4                  /* 128 logical lines per 224 physical lines */
#endif
    cmp #7
    bcc .Lphase
    sbc #7                      /* carry set by CMP */
    inc bat_source_y
.Lphase:
    sta bat_phase
#if !defined(BAT_BITMAP_DOUBLE_BUFFER)
    lda bat_source_y
    cmp #64
    bne .Lno_switch
    st0 #7                       /* BAT's second 64-column half */
    st1 #0
    st2 #2
.Lno_switch:
#endif
    st0 #8                       /* BYR = 8 * (y & 63) - 1 */
    lda bat_source_y
    and #$3f
    asl
    asl
    asl
    sec
    sbc #1
    sta $0002
    /* High byte of (((y & 63) << 3) - 1). Borrow happens at
     * EVERY multiple of 32, not only multiples of 64. Otherwise the
     * Mode 7 sky gets two dark scanlines at source rows 32/96. */
    lda bat_source_y
    lsr
    lsr
    lsr
    lsr
    lsr
    and #1
    tax
    lda bat_source_y
    and #$1f
    bne .Lno_borrow
    dex
.Lno_borrow:
    txa
    sta $0003
    st0 #6                       /* arm next scanline */
    lda bat_line
    clc
    adc #$41
    sta $0002
    cla
    adc #0
    sta $0003
.Ldone:
    ply
    plx
    pla
    rti

.size irq_vdc, .-irq_vdc
