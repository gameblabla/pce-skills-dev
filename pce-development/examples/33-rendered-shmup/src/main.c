/* Minimal rendered shmup. Background + 16x16 SAT actors, no font/audio.
 * G2TR state is derived from the exact objects submitted to SAT.
 */
#include <pce.h>
#include <stdint.h>
#include "scene_assets.h"
#include "genre_trace.h"
volatile G2Trace pce_genre_trace[2];
static volatile uint8_t ticks;
__attribute__((interrupt)) void irq_vdc(void) {
    if (*IO_VDC_STATUS & VDC_FLAG_VBLANK) ++ticks;
}
static uint8_t px, py, previous;
static uint16_t shots;
static uint8_t bx[4],by[4],live[4];
static uint8_t ex[3],ey[3];
static vdc_sprite_t sat[64];

static void publish(uint32_t frame,uint16_t buttons,uint8_t count,int8_t dx,int8_t dy) {
    volatile G2Trace *t=&pce_genre_trace[frame&1];
    uint16_t n=(uint16_t)(frame<<1);
    t->sequence=n|1;
    t->magic[0]='G';t->magic[1]='2';t->magic[2]='T';t->magic[3]='R';
    t->version=G2TR_VERSION;t->genre=G2TR_SHMUP;t->scene=1;
    t->flags=G2TR_FLAG_VISIBLE|G2TR_FLAG_ACTIVE;
    t->frame=frame;t->buttons=buttons&0xffu;
    t->x_q8=G2TR_Q8(px);t->y_q8=G2TR_Q8(py);
    t->vx_q8=G2TR_Q8(dx);t->vy_q8=G2TR_Q8(dy);
    t->camera_x_q8=t->camera_y_q8=0;
    t->screen_x_q8=t->x_q8;t->screen_y_q8=t->y_q8;
    t->state[0]=count;t->state[1]=3;t->state[2]=shots;t->state[3]=0;
    t->sequence=n;
}
static void actor(uint8_t slot,uint8_t x,uint8_t y,uint8_t tile) {
    sat[slot].x=(uint16_t)x+32;
    sat[slot].y=(uint16_t)y+64;
    sat[slot].pattern=SCENE_SPRITE_WORD/32u+tile*2u;
    sat[slot].attr=VDC_SPRITE_FG;
}
int main(void) {
    static const vdc_sprite_t blank[64]={0};
    pce_cpu_irq_disable();
    pce_vdc_bg_disable();pce_vdc_sprite_disable();
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);
    pce_vdc_set_copy_word();
    pce_vce_copy_palette(0,scene_bg_palette,1);
    pce_vce_copy_palette(16,scene_sprite_palette,1);
    pce_vdc_copy_to_vram(SCENE_BG_WORD,scene_patterns,sizeof(scene_patterns));
    pce_vdc_copy_to_vram(0,scene_bat,sizeof(scene_bat));
    pce_vdc_copy_to_vram(SCENE_SPRITE_WORD,scene_sprites,sizeof(scene_sprites));
    pce_vdc_copy_to_vram(SCENE_SAT_WORD,blank,sizeof(blank));
    pce_vdc_sprite_set_table_start(SCENE_SAT_WORD);
    pce_vdc_poke(VDC_REG_DMA_CONTROL,VDC_DMA_REPEAT_SATB);
    pce_vdc_irq_vblank_enable();pce_irq_enable(IRQ_VDC);
    pce_vdc_bg_enable();pce_vdc_sprite_enable();pce_cpu_irq_enable();
    /* Explicit run-time initialization: avoid depending on initialized .data
     * in minimal HuCard startup configurations. */
    px=120;py=188;ex[0]=40;ex[1]=120;ex[2]=199;
    ey[0]=41;ey[1]=74;ey[2]=55;
    uint32_t frame=0;
    for(;;) {
        uint8_t before=ticks;while(before==ticks) {}
        uint16_t buttons=(uint16_t)~pce_joypad_read();
        int8_t dx=0,dy=0;
        if((buttons&KEY_LEFT)&&px>8){--px;--px;dx=-2;}
        if((buttons&KEY_RIGHT)&&px<230){px+=2;dx=2;}
        if((buttons&KEY_UP)&&py>9){--py;dy=-1;}
        if((buttons&KEY_DOWN)&&py<199){++py;dy=1;}
        if((buttons&KEY_1)&&!(previous&KEY_1)) {
            for(uint8_t i=0;i<4;++i)if(!live[i]) {
                bx[i]=px+7;by[i]=py;live[i]=1;++shots;break;
            }
        }
        previous=(uint8_t)buttons;
        actor(0,px,py,0);
        for(uint8_t i=0;i<3;++i){
            if((frame&3)==0) {if(++ey[i]>=207)ey[i]=16;}
            actor(1+i,ex[i],ey[i],1);
        }
        uint8_t count=0;
        for(uint8_t i=0;i<4;++i) {
            if(live[i]) {
                if(by[i]<6)live[i]=0;
                else by[i]-=3;
            }
            if(live[i]){actor(4+i,bx[i],by[i],2);++count;}
            else sat[4+i]=(vdc_sprite_t){0};
        }
        pce_vdc_copy_to_vram(SCENE_SAT_WORD,sat,8u*sizeof(sat[0]));
        publish(frame,buttons,count,dx,dy);++frame;
    }
}
