/* GENERATED 32-event scroll IRQ; two full 128x128 BAT pages. */
.section .text.irq_vdc,"ax",@progbits
.global irq_vdc
.type irq_vdc,@function
.extern bat_frames,bat_source_y,ray_flip_front,ray_flip_pending,ray_redraws
irq_vdc:
    pha
    phx
    cld
    lda $0000
    pha
    and #$20
    beq .Lraster
    inc bat_frames
    stz bat_source_y
    lda ray_flip_pending
    beq .Lno_swap
    stz ray_flip_pending
    lda ray_flip_front
    eor #1
    sta ray_flip_front
    inc ray_redraws
    bne .Lno_swap
    inc ray_redraws+1
.Lno_swap:
    st0 #7
    st1 #0
    lda ray_flip_front
    beq .Lfirst
    st2 #2
    bra .Lpositioned
.Lfirst:
    st2 #0
.Lpositioned:
    st0 #8
    st1 #0
    st2 #0
    st0 #6
    st1 #$48
    st2 #0
.Lraster:
    pla
    and #$04
    beq .Ldone
    ldx bat_source_y
    cpx #31
    bcs .Ldone
    inx
    stx bat_source_y
    st0 #8
    lda tiled_byr_low,x
    sta $0002
    lda tiled_byr_high,x
    sta $0003
    st0 #6
    lda tiled_rcr_low,x
    sta $0002
    lda tiled_rcr_high,x
    sta $0003
.Ldone:
    plx
    pla
    rti
.size irq_vdc, .-irq_vdc
.section .rodata.irq_tables,"a",@progbits
tiled_byr_low:
    .byte $ff,$07,$0f,$17,$1f,$27,$2f,$37,$3f,$47,$4f,$57,$5f,$67,$6f,$77
    .byte $7f,$87,$8f,$97,$9f,$a7,$af,$b7,$bf,$c7,$cf,$d7,$df,$e7,$ef,$f7
tiled_byr_high:
    .byte $ff,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    .byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
tiled_rcr_low:
    .byte $48,$4f,$56,$5d,$64,$6b,$72,$79,$80,$87,$8e,$95,$9c,$a3,$aa,$b1
    .byte $b8,$bf,$c6,$cd,$d4,$db,$e2,$e9,$f0,$f7,$fe,$05,$0c,$13,$1a,$21
tiled_rcr_high:
    .byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    .byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$01,$01,$01,$01,$01
