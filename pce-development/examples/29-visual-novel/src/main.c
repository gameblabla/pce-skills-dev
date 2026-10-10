/* Static 256x224 dialogue background + just ONE animated 16x16 mouth sprite.
 * All graphics were generated OFFLINE from PNGs (make assets).
 * G2TR v2 telemetry is independent of the older platformer P2TR record.
 */
#include <pce.h>
#include "vn_assets.h"
#include "genre_trace.h"

volatile G2Trace pce_genre_trace[2];
static volatile uint8_t vblanks;
__attribute__((interrupt)) void irq_vdc(void) {
    uint8_t status=*IO_VDC_STATUS;
    if(status & VDC_FLAG_VBLANK)++vblanks;
}
static void trace_publish(uint32_t frame, uint8_t mouth) {
    volatile G2Trace *t=&pce_genre_trace[frame&1];
    uint16_t n=(uint16_t)(frame<<1);
    t->sequence=n|1;
    t->magic[0]='G';t->magic[1]='2';t->magic[2]='T';t->magic[3]='R';
    t->version=G2TR_VERSION;t->genre=G2TR_VISUAL_NOVEL;
    t->scene=1;t->flags=G2TR_FLAG_VISIBLE|G2TR_FLAG_ACTIVE;
    t->frame=frame;t->buttons=(uint16_t)~pce_joypad_read();
    t->x_q8=G2TR_Q8(VN_MOUTH_X);t->y_q8=G2TR_Q8(VN_MOUTH_Y);
    t->vx_q8=t->vy_q8=t->camera_x_q8=t->camera_y_q8=0;
    t->screen_x_q8=t->x_q8;t->screen_y_q8=t->y_q8;
    t->state[0]=1; /* static picture ID */
    t->state[1]=1; /* protagonist portrait ID */
    t->state[2]=mouth; /* mouth closed=0, open=1 */
    t->state[3]=1; /* dialogue ID */
    t->sequence=n;
}
int main(void) {
    static const vdc_sprite_t blank[64]={0};
    pce_cpu_irq_disable();
    pce_vdc_bg_disable();pce_vdc_sprite_disable();
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);
    pce_vdc_set_copy_word();
    pce_vce_copy_palette(0,vn_bg_palette,VN_BG_PALETTES);
    pce_vce_copy_palette(16,vn_sprite_palette,1);
    pce_vdc_copy_to_vram(VN_BG_WORD,vn_patterns,sizeof(vn_patterns));
    pce_vdc_copy_to_vram(0,vn_bat,sizeof(vn_bat));
    pce_vdc_copy_to_vram(VN_SPRITE_WORD,vn_mouth_patterns,sizeof(vn_mouth_patterns));
    pce_vdc_copy_to_vram(VN_SAT_WORD,blank,sizeof(blank));
    pce_vdc_sprite_set_table_start(VN_SAT_WORD);
    pce_vdc_poke(VDC_REG_DMA_CONTROL,VDC_DMA_REPEAT_SATB);
    pce_vdc_poke(VDC_REG_BG_SCROLL_X,0);
    pce_vdc_poke(VDC_REG_BG_SCROLL_Y,0);
    pce_vdc_irq_vblank_enable();pce_irq_enable(IRQ_VDC);
    pce_vdc_bg_enable();pce_vdc_sprite_enable();
    pce_cpu_irq_enable();
    uint32_t frame=0;
    for(;;) {
        uint8_t was=vblanks;
        while(was==vblanks) { }
        /* Mouth opens and closes automatically during the same dialogue. */
        uint8_t mouth=(uint8_t)((frame/12)&1);
        const vdc_sprite_t sprite={(uint16_t)(VN_MOUTH_Y+64),
            (uint16_t)(VN_MOUTH_X+32),
            (uint16_t)(VN_SPRITE_WORD/32u+(mouth?2u:0u)), VDC_SPRITE_FG};
        pce_vdc_copy_to_vram(VN_SAT_WORD,&sprite,sizeof(sprite));
        trace_publish(frame,mouth);
        ++frame;
    }
}
