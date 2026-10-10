/* Native HuC6280 raster IRQ for the 512x224 BAT pseudo-bitmap.
 * Replaces the compiler-generated interrupt prologue and volatile VDC
 * register writes with direct ST0/ST1/ST2. Preserve A/X/Y and RTI.
 * Source rows are 128, expanded over 224 CRT lines with +4/7 phase.
 * The 128x64 BAT is read in two 64-column halves; BXR changes only
 * when source_y crosses into the second half (row 64).
 */
.section .text.irq_vdc,"ax",@progbits
.global irq_vdc
.type irq_vdc,@function
.extern bat_frames,bat_line,bat_source_y,bat_phase
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
    st0 #7                       /* BXR=0 */
    st1 #0
    st2 #0
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
    adc #4
    cmp #7
    bcc .Lphase
    sbc #7                      /* carry set by CMP */
    inc bat_source_y
.Lphase:
    sta bat_phase
    lda bat_source_y
    cmp #64
    bne .Lno_switch
    st0 #7                       /* BAT's second 64-column half */
    st1 #0
    st2 #2
.Lno_switch:
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
