/* Wolf3D-style 2.5D raycaster rendered through PCEdev's 512x224
 * paired-BAT pseudo-bitmap: 128x128 logical pixels, two 4-bit pixels per BAT
 * word, 256 permanent patterns. NO per-frame planar tile uploads.
 * Rays, wall geometry, textures, ceiling and floor are all drawn as pixels.
 * LEFT/RIGHT turn, UP/DOWN walk, with independent solid-cell collision.
 */
#include <pce.h>
#include <stdint.h>
#include "genre_trace.h"
#include "ray_tables.h"
#include "bat_bitmap.h"
volatile G2Trace pce_genre_trace[2];

static const uint8_t map[8][8]={
 {1,1,1,1,1,1,1,1},
 {1,0,0,0,0,0,0,1},
 {1,0,2,0,0,0,0,1},
 {1,0,0,0,0,3,0,1},
 {1,0,0,0,0,0,0,1},
 {1,0,0,2,0,0,0,1},
 {1,0,0,0,0,0,0,1},
 {1,1,1,1,1,1,1,1}
};
/* All 16 entries have a purpose. 0 is also the backdrop and must be opaque. */
static const uint16_t colors[16]={
 VCE_COLOR(0,0,1), VCE_COLOR(0,0,2), VCE_COLOR(0,1,3),
 VCE_COLOR(1,2,4), VCE_COLOR(2,3,4), VCE_COLOR(2,1,0),
 VCE_COLOR(3,2,1), VCE_COLOR(1,1,1), VCE_COLOR(2,1,1),
 VCE_COLOR(3,2,1), VCE_COLOR(5,2,1), VCE_COLOR(6,4,2),
 VCE_COLOR(2,2,2), VCE_COLOR(4,4,4), VCE_COLOR(6,6,6),
 VCE_COLOR(7,6,4)
};
static int16_t world_x,world_y;
static uint8_t angle,wall_blocked;
static uint16_t near_depth,far_depth,hit_count;
/* 32 real rays, four logical pixels wide. No per-pixel ray traversal. */
static uint8_t depth[32],top[32],tex_u[32],wall_kind[32];
/* Four scanlines in RAM for a VBlank-only 512-byte BAT upload.
 * The complete framebuffer remains the 8 Kiword VDC BAT, not CPU RAM. */
static uint16_t scan_words[4][64];
static uint8_t draw_row;

static uint8_t material_at(int16_t x,int16_t y) {
    int16_t tx=x>>8,ty=y>>8;
    if(tx<0||tx>=8||ty<0||ty>=8)return 1;
    return map[ty][tx];
}
static uint8_t cast_ray(uint8_t col) {
    const int8_t dx=ray_step_x[angle][col],dy=ray_step_y[angle][col];
    int16_t x=world_x,y=world_y;
    for(uint8_t n=1;n<=32;++n) {
        int16_t px=x;
        x+=dx;y+=dy;
        uint8_t m=material_at(x,y);
        if(m) {
            /* Pick the hit wall's horizontal coordinate from the axis crossed.
             * The 8px texture is repeated and brick joints break repetition. */
            tex_u[col]=(uint8_t)(((px>>8)!=(x>>8)?y:x)>>5)&7u;
            if((px>>8)!=(x>>8))m|=0x80u; /* darken X-facing walls */
            wall_kind[col]=m;
            return n;
        }
    }
    tex_u[col]=0;wall_kind[col]=1;
    return 32;
}
__attribute__((noinline)) static void cast_scene(void) {
    near_depth=0xffff;far_depth=0;hit_count=0;
    for(uint8_t c=0;c<32;++c) {
        uint8_t d=cast_ray(c);
        depth[c]=d;
        top[c]=(uint8_t)((128u-wall_height[d])>>1);
        if(d<near_depth)near_depth=d;
        if(d>far_depth)far_depth=d;
        if(d<32)++hit_count;
    }
}
/* Bitmap texel shader: colour indices, not planar tile indices.
 * Wall_v is an offline-generated lookup, so this draws without target
 * multiply/divide and without compiler software math helpers. */
static uint8_t wall_pixel(uint8_t c,uint8_t u,uint8_t y) {
    uint8_t d=depth[c],v=wall_tex_v[d][(uint8_t)(y-top[c])>>1];
    uint8_t m=wall_kind[c]&0x7fu;
    if(m==3) { /* gold/metal doorway, ribbing and vertical highlights */
        if((u&7u)==0 || (v&7u)==0)return 7;
        return ((u+v)&3u)==0?15:11;
    }
    if(m==2) { /* brick wall with offset mortar between courses */
        if((v&3u)==0 || ((uint8_t)(u+((v&4u)?4u:0u))&7u)==0)return 7;
        return d>13?8:(((u^v)&2u)?10:9);
    }
    /* irregular cut stone with joints, shading and a lit upper edge */
    if((v&7u)==0 || ((uint8_t)(u+((v&8u)?3u:0u))&7u)==0)return 7;
    if(d>16 || (wall_kind[c]&0x80u))return 12;
    return ((u^v)&3u)==0?15:13;
}
static uint8_t floor_color(uint8_t u,uint8_t v) {
    if((u&31u)==0u || (v&31u)==0u)return 7u;
    return (((u>>4)^(v>>4))&1u)?5u:6u;
}
/* Return two independent 4-bit pixel indices packed into one BAT word.
 * Unlike a flat-column renderer, both halves of the pair are sampled. */
static uint8_t bitmap_pair(uint8_t pair,uint8_t y) {
    uint8_t c=pair>>1;
    uint8_t d=depth[c],t=top[c];
    if(y<t) {
        uint8_t sky=y<16u?0u:y<32u?1u:y<48u?2u:3u;
        return (uint8_t)((sky<<4)|sky);
    }
    if((uint8_t)(y-t)<wall_height[d]) {
        uint8_t u=(uint8_t)(tex_u[c]+((pair&1u)<<1))&7u;
        return (uint8_t)((wall_pixel(c,u,y)<<4)|wall_pixel(c,(u+1u)&7u,y));
    }
    /* A perspective floor: two nearby horizontal samples, independent
     * palette nibbles, and no runtime multiply/divide. */
    /* The perspective scale has only 5 possible values. Constant ASLs
     * beat the compiler's variable 16-bit __ashlhi3 helper (measured). */
    uint8_t fu,fv,delta;
    switch(floor_shift[y]) {
        case 4: fu=(uint8_t)(pair<<4);fv=(uint8_t)(y<<4);delta=8;break;
        case 3: fu=(uint8_t)(pair<<3);fv=(uint8_t)(y<<3);delta=4;break;
        case 2: fu=(uint8_t)(pair<<2);fv=(uint8_t)(y<<2);delta=2;break;
        case 1: fu=(uint8_t)(pair<<1);fv=(uint8_t)(y<<1);delta=1;break;
        default:fu=pair;fv=y;delta=1;break;
    }
    fu=(uint8_t)(fu+(uint8_t)(world_x>>5));
    fv=(uint8_t)(fv+(uint8_t)(world_y>>5));
    return (uint8_t)((floor_color(fu,fv)<<4)|floor_color((uint8_t)(fu+delta),fv));
}
/* Render four logical bitmap lines into RAM, then commit in VBlank.
 * Unlike active-display writes, this cannot starve the per-scanline raster
 * callback; missed HBlank IRQs otherwise left most of the picture sky-blue.
 * This example assumes the 4*64-word upload fits in VBlank; hardware
 * cycle timing has not yet been measured. */
static void render_slice(void) {
    if(draw_row==0u)cast_scene();
    for(uint8_t i=0;i<4u;++i) {
        uint8_t y=(uint8_t)(draw_row+i);
        for(uint8_t pair=0;pair<64u;++pair)
            scan_words[i][pair]=(uint16_t)(0xf200u|bitmap_pair(pair,y));
    }
    /* Wait specifically for the NEXT vertical blank. No RCR writes execute
     * while interrupts are masked; the raster remap is idle in VBlank. */
    uint8_t before=bat_frames;
    while(bat_frames==before){}
    pce_cpu_irq_disable();
    for(uint8_t i=0;i<4u;++i) {
        uint8_t y=(uint8_t)(draw_row+i);
        uint16_t address=((uint16_t)(y&63u)<<7)+((y&64u)?64u:0u);
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,address);
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
        for(uint8_t pair=0;pair<64u;++pair)*IO_VDC_DATA=scan_words[i][pair];
    }
    pce_cpu_irq_enable();
    draw_row=(draw_row+4u)&127u;
}
__attribute__((noinline))
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
    t->state[2]=near_depth<<6;t->state[3]=far_depth<<6;
    t->sequence=n;
}
int main(void) {
    bat_bitmap_setup(colors);
    world_x=3*256+128;world_y=3*256+128;angle=0;
    bat_bitmap_display();
    draw_row=0;
    uint32_t frame=0;
    for(;;) {
        uint8_t before=bat_frames;while(before==bat_frames){}
        uint8_t buttons=(uint8_t)~pce_joypad_read();
        if((frame&5u)==0) {
            if(buttons&KEY_LEFT)angle=(angle+15u)&15u;
            if(buttons&KEY_RIGHT)angle=(angle+1u)&15u;
        }
        int16_t old_x=world_x,old_y=world_y;
        wall_blocked=0;
        if(buttons&(KEY_UP|KEY_DOWN)) {
            int16_t x=world_x,y=world_y;
            if(buttons&KEY_UP){x+=player_step_x[angle];y+=player_step_y[angle];}
            else{x-=player_step_x[angle];y-=player_step_y[angle];}
            if(material_at(x,world_y))wall_blocked=1;else world_x=x;
            if(material_at(world_x,y))wall_blocked=1;else world_y=y;
        }
        render_slice();
        publish(frame,buttons,world_x-old_x,world_y-old_y);++frame;
    }
}
