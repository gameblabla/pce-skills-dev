/* Tiny perspective-road scene with movable car and advancing traffic sprites.
 * This demonstrates race world/lane state, not the separate 512x224 Mode 7 trick.
 * G2TR values are derived from the onscreen car and travelled distance.
 */
#include <pce.h>
#include <stdint.h>
#include "scene_assets.h"
#include "genre_trace.h"
volatile G2Trace pce_genre_trace[2];
static volatile uint8_t ticks;
__attribute__((interrupt)) void irq_vdc(void) {
    if(*IO_VDC_STATUS & VDC_FLAG_VBLANK)++ticks;
}
static uint8_t car_x;
static uint16_t distance;
static uint8_t crash_cooldown,checkpoint_hold,collision_hold;
static vdc_sprite_t sat[64];
static void actor(uint8_t slot,uint8_t x,uint8_t y,uint8_t sprite) {
    sat[slot].x=(uint16_t)x+32;
    sat[slot].y=(uint16_t)y+64;
    sat[slot].pattern=SCENE_SPRITE_WORD/32u+sprite*2u;
    sat[slot].attr=VDC_SPRITE_FG;
}
static void publish(uint32_t frame,uint16_t buttons,uint8_t speed,int8_t dx,uint8_t collided,uint8_t checkpoint) {
    volatile G2Trace *t=&pce_genre_trace[frame&1];
    uint16_t n=(uint16_t)(frame<<1);
    t->sequence=n|1;
    t->magic[0]='G';t->magic[1]='2';t->magic[2]='T';t->magic[3]='R';
    t->version=G2TR_VERSION;t->genre=G2TR_RACING;t->scene=1;
    t->flags=G2TR_FLAG_VISIBLE|G2TR_FLAG_ACTIVE|
             (collided?G2TR_FLAG_COLLIDING:0)|
             (checkpoint?G2TR_FLAG_TRANSITION:0);
    t->frame=frame;t->buttons=buttons&0xffu;
    t->x_q8=G2TR_Q8(car_x);t->y_q8=G2TR_Q8(181);
    t->vx_q8=G2TR_Q8(dx);t->vy_q8=G2TR_Q8(speed);
    t->camera_x_q8=t->camera_y_q8=0;
    t->screen_x_q8=t->x_q8;t->screen_y_q8=t->y_q8;
    t->state[0]=G2TR_Q8((int16_t)car_x-120);
    t->state[1]=G2TR_Q8(distance);
    t->state[2]=G2TR_Q8(speed);
    t->state[3]=3;
    t->sequence=n;
}
int main(void) {
    static const vdc_sprite_t blank[64]={0};
    pce_cpu_irq_disable();pce_vdc_bg_disable();pce_vdc_sprite_disable();
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);pce_vdc_set_copy_word();
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
    car_x=120;distance=0;crash_cooldown=0;checkpoint_hold=collision_hold=0;
    uint32_t frame=0;
    for(;;) {
        uint8_t before=ticks;while(before==ticks) {}
        uint16_t buttons=(uint16_t)~pce_joypad_read();
        int8_t dx=0;
        if((buttons&KEY_LEFT)&&car_x>80){car_x-=2;dx=-2;}
        if((buttons&KEY_RIGHT)&&car_x<160){car_x+=2;dx=2;}
        uint8_t speed=(buttons&KEY_UP)?3:((buttons&KEY_DOWN)?0:1);
        if(crash_cooldown) {--crash_cooldown;if(speed>1)speed=1;}
        uint16_t before_distance=distance;
        distance+=speed;
        uint8_t checkpoint=(distance/64u != before_distance/64u);
        uint8_t collided=0;
        actor(0,car_x,181,0);
        for(uint8_t i=0;i<3;++i){
            /* Traffic approaches the player as world progress increases. */
            uint8_t track_y=(uint8_t)(((distance/(1u+i)+i*55u)%176u)+25u);
            uint8_t traffic_x=(uint8_t)(96u+i*24u);
            actor(1+i,traffic_x,track_y,(uint8_t)(1+i));
            if(!crash_cooldown && (int16_t)traffic_x<(int16_t)car_x+13 &&
               (int16_t)traffic_x+13>(int16_t)car_x &&
               track_y<195 && track_y+13>181) {
                collided=1;crash_cooldown=18;
            }
        }
        pce_vdc_copy_to_vram(SCENE_SAT_WORD,sat,4u*sizeof(sat[0]));
        if(checkpoint)checkpoint_hold=3;
        else if(checkpoint_hold)--checkpoint_hold;
        if(collided)collision_hold=3;
        else if(collision_hold)--collision_hold;
        publish(frame,buttons,speed,dx,collision_hold!=0,checkpoint_hold!=0);++frame;
    }
}
