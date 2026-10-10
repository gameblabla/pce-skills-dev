/* Small actual raycaster: fixed-point Q8 map, 32 rays, 8px BG columns.
 * The 256x224 background is redrawn by rewriting the BAT only, not patterns.
 * NO audio, fonts, sprite renderer or pre-rendered viewpoint pictures.
 */
#include <pce.h>
#include <stdint.h>
#include "genre_trace.h"
#include "ray_tables.h"
volatile G2Trace pce_genre_trace[2];
static volatile uint8_t ticks;
__attribute__((interrupt)) void irq_vdc(void) {
    if(*IO_VDC_STATUS & VDC_FLAG_VBLANK)++ticks;
}
static const uint8_t map[8][8]={
 {1,1,1,1,1,1,1,1},
 {1,0,0,0,0,0,0,1},
 {1,0,1,0,0,0,0,1},
 {1,0,0,0,0,1,0,1},
 {1,0,0,0,0,0,0,1},
 {1,0,0,1,0,0,0,1},
 {1,0,0,0,0,0,0,1},
 {1,1,1,1,1,1,1,1}
};
static const uint16_t colors[16]={
 0x001,0x041,0x042,0x08b,0x0d4,0x11c,0x11d,0x08a,0x051,0x092,0x09a,0x0e2,0x12b,0x174,0x1bd,0x1bd
};
static uint8_t tiles[16*32];
static uint16_t bat[32*28];
static int16_t world_x,world_y;
static uint8_t angle;
static uint16_t near_depth,far_depth,hit_count;
static uint8_t wall_blocked;

static uint8_t is_wall(int16_t x,int16_t y) {
    int16_t tx=x>>8,ty=y>>8;
    if(tx<0||tx>=8||ty<0||ty>=8)return 1;
    return map[ty][tx];
}
/* A quarter-cell DDA in Q8. One step is approximately 64/256 map unit.
 * Both columns and trace depths are computed from these same ray results. */
static uint8_t ray_hit(uint8_t col) {
    const int8_t dx=ray_step_x[angle][col];
    const int8_t dy=ray_step_y[angle][col];
    int16_t x=world_x,y=world_y;
    for(uint8_t n=1;n<=32;++n) {
        x+=dx;y+=dy;
        if(is_wall(x,y))return n;
    }
    return 0; /* no wall reached within ray budget */
}
static void render(void) {
    for(uint8_t y=0;y<28;++y)for(uint8_t x=0;x<32;++x)
        bat[(uint16_t)y*32+x]=sky_bat[y];
    near_depth=0xffff;far_depth=0;hit_count=0;
    for(uint8_t x=0;x<32;++x) {
        uint8_t depth=ray_hit(x);
        if(depth)++hit_count;else depth=32;
        if(depth<near_depth)near_depth=depth;
        if(depth>far_depth)far_depth=depth;
        uint8_t height=wall_height[depth];
        uint8_t top=(uint8_t)(14u-height/2u);
        uint8_t bottom=top+height;
        uint16_t tile=wall_shade[depth];
        for(uint8_t y=top;y<bottom && y<28;++y)
            bat[(uint16_t)y*32+x]=0x0080u+tile;
    }
    pce_vdc_copy_to_vram(0,bat,sizeof(bat));
}
static void publish(uint32_t frame,uint16_t buttons,int16_t moved_x,int16_t moved_y) {
    volatile G2Trace *t=&pce_genre_trace[frame&1];
    uint16_t n=(uint16_t)(frame<<1);
    t->sequence=n|1;
    t->magic[0]='G';t->magic[1]='2';t->magic[2]='T';t->magic[3]='R';
    t->version=G2TR_VERSION;t->genre=G2TR_RAYCASTER;t->scene=1;
    t->flags=G2TR_FLAG_VISIBLE|G2TR_FLAG_ACTIVE|
             (wall_blocked?G2TR_FLAG_COLLIDING:0);
    t->frame=frame;t->buttons=buttons&0xffu;
    t->x_q8=world_x;t->y_q8=world_y;t->vx_q8=moved_x;t->vy_q8=moved_y;
    t->camera_x_q8=t->camera_y_q8=0;
    t->screen_x_q8=t->screen_y_q8=0;
    t->state[0]=32;t->state[1]=hit_count;
    t->state[2]=(int32_t)near_depth*64;t->state[3]=(int32_t)far_depth*64;
    t->sequence=n;
}
int main(void) {
    pce_cpu_irq_disable();pce_vdc_bg_disable();
    pce_vdc_set_resolution(256,224,VCE_PIXEL_CLOCK_5MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_32_32);pce_vdc_set_copy_word();
    pce_vce_copy_palette(0,colors,1);
    for(uint8_t t=0;t<16;++t) {
        for(uint8_t y=0;y<8;++y)for(uint8_t p=0;p<4;++p)
            tiles[(uint16_t)t*32+(uint16_t)(p/2)*16+y*2+p%2]=((t>=9 && y==0 ? t-1 : t)&(1u<<p))?0xff:0;
    }
    pce_vdc_copy_to_vram(0x0800,tiles,sizeof(tiles));
    pce_vdc_irq_vblank_enable();pce_irq_enable(IRQ_VDC);
    pce_vdc_bg_enable();pce_cpu_irq_enable();
    world_x=3*256+128;world_y=3*256+128;angle=0;
    render();
    uint32_t frame=0;
    for(;;) {
        uint8_t before=ticks;while(before==ticks) {}
        uint16_t buttons=(uint16_t)~pce_joypad_read();
        if((frame&5)==0) {
            if(buttons&KEY_LEFT)angle=(angle+15)&15;
            if(buttons&KEY_RIGHT)angle=(angle+1)&15;
        }
        int16_t old_x=world_x,old_y=world_y;
        wall_blocked=0;
        if((buttons&(KEY_UP|KEY_DOWN))!=0) {
            int16_t x=world_x, y=world_y;
            if (buttons&KEY_UP) { x+=player_step_x[angle]; y+=player_step_y[angle]; }
            else { x-=player_step_x[angle]; y-=player_step_y[angle]; }
            /* Check X and Y independently: this permits sliding along walls,
             * but never allows the camera centre to enter a solid map cell. */
            if(is_wall(x,world_y))wall_blocked=1;
            else world_x=x;
            if(is_wall(world_x,y))wall_blocked=1;
            else world_y=y;
        }
        if((frame&7)==0)render();
        publish(frame,buttons,world_x-old_x,world_y-old_y);++frame;
    }
}
