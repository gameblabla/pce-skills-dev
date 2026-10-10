/* Wolf3D-style 2.5D raycaster rendered through PCEdev's 512x224
 * paired-BAT pseudo-bitmap: default 128x128 logical pixels (optional
 * 128x64 atomic double-page mode), two 4-bit pixels per BAT
 * word, 256 permanent patterns. NO per-frame planar tile uploads.
 * Rays, wall geometry, textures, ceiling and floor are all drawn as pixels.
 * LEFT/RIGHT turn, UP/DOWN walk, with independent solid-cell collision.
 */
#include <pce.h>
#include <stdint.h>
#include "genre_trace.h"
#include "ray_tables.h"
#include "wall_pairs.h"
#ifndef RAY_DOUBLE_BUFFER
#define RAY_DOUBLE_BUFFER 0
#endif
#if !RAY_DOUBLE_BUFFER
#include "sheet_pairs.h"
#include "sheet_palette.h"
#define RAY_ACTIVE_PAIRS ray_sheet_pairs
#define RAY_U_MASK 15u
#else
#define RAY_ACTIVE_PAIRS ray_wall_pairs
#define RAY_U_MASK 7u
#endif
#ifndef RAY_FAST_SPANS
#define RAY_FAST_SPANS 1
#endif
#if RAY_FAST_SPANS && !RAY_DOUBLE_BUFFER
#include "backdrop_words.h"
#endif
#include "bat_bitmap.h"
#ifndef RAY_DOUBLE_BUFFER
#define RAY_DOUBLE_BUFFER 0
#endif
#if RAY_DOUBLE_BUFFER
#ifndef BAT_BITMAP_DOUBLE_BUFFER
#error "RAY_DOUBLE_BUFFER requires BAT_BITMAP_DOUBLE_BUFFER in the IRQ"
#endif
#define RAY_LOGICAL_ROWS 64u
#else
#define RAY_LOGICAL_ROWS 128u
#endif
volatile G2Trace pce_genre_trace[2];

static const uint8_t map[8][8]={
 {1,2,2,3,3,4,5,6},
 {1,0,0,0,0,0,0,6},
 {1,0,2,0,0,0,0,6},
 {1,0,0,0,0,3,0,7},
 {1,0,0,0,0,0,0,7},
 {1,0,0,2,0,0,0,7},
 {1,0,0,0,0,0,0,7},
 {1,2,2,3,3,4,5,6}
};
/* All 16 entries have a purpose. 0 is also the backdrop and must be opaque. */
static const __attribute__((unused)) uint16_t colors[16]={
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
/* Fourteen pre-quantized source-sheet material/shade classes in full detail. */
static uint8_t wall_style[32];
#ifndef RAY_WALL_LOOKUP
#define RAY_WALL_LOOKUP 1
#endif
/* Explicit renderer variants for reproducible SAME-SOURCE benchmarks.
 * Default: eight logical rows via TIA during VBlank (1024 bytes).
 * Benchmark variant: four rows (512 bytes) with the same TIA transfer path.
 * This transfers BAT words only; no software framebuffer or planar conversion.
 */
#ifndef RAY_SLICE_ROWS
#define RAY_SLICE_ROWS 8
#endif
#ifndef RAY_UPLOAD_TIA
#define RAY_UPLOAD_TIA 1
#endif
#ifndef RAY_DIRECT_CHUNKS
#define RAY_DIRECT_CHUNKS 0
#endif
#if RAY_SLICE_ROWS != 4 && RAY_SLICE_ROWS != 8
#error "RAY_SLICE_ROWS must be 4 or 8, dividing 128 exactly"
#endif
#if RAY_UPLOAD_TIA != 0 && RAY_UPLOAD_TIA != 1
#error "RAY_UPLOAD_TIA must be 0 or 1"
#endif
#ifndef RAY_COLUMN_STREAM
#define RAY_COLUMN_STREAM 1
#endif
#if RAY_DOUBLE_BUFFER
#undef RAY_COLUMN_STREAM
#define RAY_COLUMN_STREAM 0
#endif
#if RAY_COLUMN_STREAM && !RAY_FAST_SPANS
#error "Column streaming requires the generated background"
#endif
#if RAY_COLUMN_STREAM
#ifndef RAY_BAT_ADDRESS_LUT
#define RAY_BAT_ADDRESS_LUT 1
#endif
#if RAY_BAT_ADDRESS_LUT
static uint16_t ray_bat_addresses[128];
#define RAY_BAT_ADDRESS(y,pair) ((uint16_t)(ray_bat_addresses[(uint8_t)(y)]+(pair)))
#else
#define RAY_BAT_ADDRESS(y,pair) ((uint16_t)((((uint16_t)((y)&63u))<<7)+(((y)&64u)?64u:0u)+(pair)))
#endif
#ifndef RAY_COLUMNS_PER_UPDATE
#define RAY_COLUMNS_PER_UPDATE 8u
#endif
#ifndef RAY_COLUMN_CHUNK_WORDS
#define RAY_COLUMN_CHUNK_WORDS 8u
#endif
static uint8_t next_column,cast_valid,cast_angle;
static int16_t cast_x,cast_y;
static uint8_t old_top[32],old_height[32],old_tex[32],old_style[32],old_depth[32];
static uint8_t column_pass_dirty;
volatile uint16_t ray_bat_words;
#ifndef RAY_COLUMN_TIA
#define RAY_COLUMN_TIA 1
#endif
/* PCEdev-style generated eight-word vertical writer. Keep a C/TIA
 * reference build (-DRAY_WALL_CODEGEN=0) for exact visual comparisons. */
#ifndef RAY_WALL_CODEGEN
#define RAY_WALL_CODEGEN 1
#endif
#ifndef RAY_CODEGEN_FAST_SETUP
#define RAY_CODEGEN_FAST_SETUP 1
#endif
#if RAY_WALL_CODEGEN
extern const uint16_t ray_codegen_handlers[33][16];
extern void ray_codegen_emit(void);
extern void ray_codegen_emit_legacy(void);
volatile uint16_t ray_codegen_target;
volatile uint16_t ray_codegen_vram_address;
volatile uint8_t ray_codegen_variant;
volatile uint16_t ray_codegen_words;
#endif
static uint16_t column_words[RAY_COLUMN_CHUNK_WORDS];
#endif
static uint16_t scan_words[RAY_SLICE_ROWS][64];
/* Independently observable completed BAT passes; increment only AFTER VRAM
 * data has been transferred, never when a render begins or a trace publishes. */
volatile uint16_t ray_redraws;
static int16_t render_world_x,render_world_y;
static uint8_t draw_row;
#if RAY_DOUBLE_BUFFER
static uint8_t draw_page;
#endif

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
            tex_u[col]=(uint8_t)(((px>>8)!=(x>>8)?y:x)>>4)&RAY_U_MASK;
            if((px>>8)!=(x>>8))m|=0x80u;
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
        uint8_t material=(uint8_t)(wall_kind[c]&0x7fu);
#if !RAY_DOUBLE_BUFFER
        wall_style[c]=(uint8_t)((((material?material:1u)-1u)<<1) |
             ((d>16u || (wall_kind[c]&0x80u))?1u:0u));
#else
        wall_style[c]=(material==3u)?4u:(material==2u)?
            ((d>13u)?3u:2u):
            ((d>16u || (wall_kind[c]&0x80u))?1u:0u);
#endif
    }
}
/* Bitmap texel shader: colour indices, not planar tile indices.
 * Wall_v is an offline-generated lookup, so this draws without target
 * multiply/divide and without compiler software math helpers. */
#if !RAY_WALL_LOOKUP
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
#endif
static __attribute__((unused)) uint8_t floor_color(uint8_t u,uint8_t v) {
    if((u&31u)==0u || (v&31u)==0u)return 7u;
    return (((u>>4)^(v>>4))&1u)?5u:6u;
}
/* Return two independent 4-bit pixel indices packed into one BAT word.
 * Unlike a flat-column renderer, both halves of the pair are sampled. */
static __attribute__((unused)) uint8_t bitmap_pair(uint8_t pair,uint8_t y) {
    uint8_t c=pair>>1;
    uint8_t d=depth[c],t=top[c];
    if(y<t) {
        uint8_t sky=y<16u?0u:y<32u?1u:y<48u?2u:3u;
        return (uint8_t)((sky<<4)|sky);
    }
    if((uint8_t)(y-t)<wall_height[d]) {
        uint8_t u=(uint8_t)(tex_u[c]+((pair&1u)<<1))&RAY_U_MASK;
#if RAY_WALL_LOOKUP
        /* One ROM lookup yields both 4-bit texels. All table strides are
         * powers of two: no runtime multiply/divide, texture branching or
         * duplicate wall shader evaluations in the inner BAT row loop. */
        uint8_t v=wall_tex_v[d][(uint8_t)(y-t)>>1];
        return RAY_ACTIVE_PAIRS[wall_style[c]][u][v];
#else
        return (uint8_t)((wall_pixel(c,u,y)<<4)|wall_pixel(c,(u+1u)&7u,y));
#endif
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
    fu=(uint8_t)(fu+(uint8_t)(render_world_x>>5));
    fv=(uint8_t)(fv+(uint8_t)(render_world_y>>5));
    return (uint8_t)((floor_color(fu,fv)<<4)|floor_color((uint8_t)(fu+delta),fv));
}
/* Build a bounded RAM staging batch, then transfer BAT entries ONLY in VBlank.
 * Each TIA sends 128 bytes to alternating VDC data ports ($0002/$0003),
 * autoincrementing the VRAM word address. TIA masks IRQs until completion:
 * the bounded eight-row / 1024-byte batch MUST remain within VBlank.
 * Unsupported larger batches have NOT been validated on hardware.
 * Cache camera position once per 128-row redraw so its textured floor never
 * combines pixels from multiple player positions inside the same pass.
 */
static __attribute__((unused)) void render_slice(void) {
    if(draw_row==0u) {
        render_world_x=world_x;render_world_y=world_y;
        cast_scene();
    }
#if RAY_FAST_SPANS && !RAY_DOUBLE_BUFFER
    /* Entire base is ROM-resident paired BAT words. Copying has no
     * divide/texture branches; CPU work scales with visible wall spans,
     * not the complete sky/floor raster. The atomic variant remains a
     * separate rendering mode and uses the original shader. */
    for(uint8_t i=0;i<RAY_SLICE_ROWS;++i) {
        uint8_t y=(uint8_t)(draw_row+i);
        for(uint8_t pair=0;pair<64u;++pair)
            scan_words[i][pair]=ray_backdrop_row(y)[pair];
    }
    for(uint8_t c=0;c<32u;++c) {
        uint8_t t=top[c],h=wall_height[depth[c]];
        uint8_t first=(t>draw_row)?t:draw_row;
        uint8_t limit=(uint8_t)(draw_row+RAY_SLICE_ROWS);
        uint8_t bottom=(uint8_t)(t+h);
        if(bottom<limit)limit=bottom;
        if(first>=limit)continue;
        uint8_t u=(uint8_t)(tex_u[c]&RAY_U_MASK);
        const uint8_t *a=RAY_ACTIVE_PAIRS[wall_style[c]][u];
        const uint8_t *b=RAY_ACTIVE_PAIRS[wall_style[c]][(u+2u)&RAY_U_MASK];
        const uint8_t *v=&wall_tex_v[depth[c]][(uint8_t)(first-t)>>1];
        uint8_t odd=(uint8_t)(first-t)&1u;
        uint16_t *dst=&scan_words[first-draw_row][(uint8_t)(c<<1)];
        for(uint8_t y=first;y<limit;++y) {
            uint8_t index=*v;
            dst[0]=(uint16_t)(0xf200u|a[index]);
            dst[1]=(uint16_t)(0xf200u|b[index]);
            dst+=64;
            if(odd)++v;
            odd^=1u;
        }
    }
#else
    for(uint8_t i=0;i<RAY_SLICE_ROWS;++i) {
        uint8_t y=(uint8_t)(draw_row+i);
#if RAY_DOUBLE_BUFFER
        /* Vertical 2:1 downsampling buys the second BAT page. */
        y=(uint8_t)(y<<1);
#endif
        for(uint8_t pair=0;pair<64u;++pair)
            scan_words[i][pair]=(uint16_t)(0xf200u|bitmap_pair(pair,y));
    }
#endif
    /* Wait specifically for the NEXT vertical blank. No RCR writes execute
     * while interrupts are masked; the raster remap is idle in VBlank. */
#if !RAY_DIRECT_CHUNKS
    uint8_t before=bat_frames;
    while(bat_frames==before){}
    pce_cpu_irq_disable();
#endif
    for(uint8_t i=0;i<RAY_SLICE_ROWS;++i) {
        uint8_t y=(uint8_t)(draw_row+i);
#if RAY_DOUBLE_BUFFER
        uint16_t address=((uint16_t)y<<7)+(draw_page?64u:0u);
#else
        uint16_t address=((uint16_t)(y&63u)<<7)+((y&64u)?64u:0u);
#endif
#if RAY_DIRECT_CHUNKS
        /* Interrupts remain enabled while shading. Each VDC write burst
         * is only eight BAT words (16 bytes), bounded across raster IRQs. */
        for(uint8_t base=0;base<64;base+=8u) {
            pce_cpu_irq_disable();
            pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,(uint16_t)(address+base));
            *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
            pce_memop((void *)IO_VDC_DATA,&scan_words[i][base],16u,PCE_MEMOP_INCR_ALT);
            pce_cpu_irq_enable();
        }
#else
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,address);
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;

#if RAY_UPLOAD_TIA
        pce_memop((void *)IO_VDC_DATA, scan_words[i], 128u, PCE_MEMOP_INCR_ALT);
#else
        for(uint8_t pair=0;pair<64u;++pair)*IO_VDC_DATA=scan_words[i][pair];
#endif
#endif /* RAY_DIRECT_CHUNKS */
    }
#if !RAY_DIRECT_CHUNKS
    pce_cpu_irq_enable();
#endif
    draw_row=(draw_row+RAY_SLICE_ROWS)&(RAY_LOGICAL_ROWS-1u);
    if(draw_row==0u) {
#if RAY_DOUBLE_BUFFER
        /* Stop until the IRQ has presented this entire back page at VBlank.
         * Never write a partially rendered image to the visible half. */
        bat_ready_page=draw_page;
        while(bat_ready_page!=0xffu){}
        draw_page^=1u;
#else
        ++ray_redraws;
#endif
    }
}
#if RAY_COLUMN_STREAM
/* This is the crucial difference from a framebuffer + full-frame TIA:
 * each 8-word VRAM burst writes VERTICALLY, using the VDC's ADD_128 stride.
 * At an angle/movement change only damaged wall spans need be restored,
 * not the sky and floor. All raster IRQs remain enabled between bursts.
 * The background lives in VDC VRAM, not an 8K RAM framebuffer.
 */
static void column_background_init(void) {
    for(uint8_t y=0;y<128u;++y) {
        uint16_t addr=(uint16_t)((((uint16_t)y&63u)<<7)+((y&64u)?64u:0u));
#if RAY_BAT_ADDRESS_LUT
        ray_bat_addresses[y]=addr;
#endif
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,addr);
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
        /* IRQs disabled by bat_bitmap_setup; initial 128-byte TIA safe. */
        pce_memop((void*)IO_VDC_DATA,ray_backdrop_row(y),128u,PCE_MEMOP_INCR_ALT);
    }
}
static void column_upload(uint8_t pair,uint8_t first,uint8_t last,
                          uint8_t c,uint8_t u) {
    const uint8_t t=top[c],end=(uint8_t)(t+wall_height[depth[c]]);
    const uint8_t *wall=RAY_ACTIVE_PAIRS[wall_style[c]][u];
    const uint8_t *tex=wall_tex_v[depth[c]];

    uint8_t texphase=0u;
    if(first>t) {
        uint8_t off=(uint8_t)(first-t);
        tex+=off>>1;
        texphase=off&1u;
    }
    for(uint8_t y=first;y<last;) {
#if RAY_WALL_CODEGEN
        /* A complete 8-pixel wall block needs no staging, loop, or V
         * index computations on the target. The generated instruction
         * sequence reads fixed ROM texture offsets and writes the VDC.
         * Only short IRQ-masked bursts are permitted; never cross either
         * 64-row BAT half or the old/new dirty-span boundary. */
        if(y>=t && (uint8_t)(y-t)%8u==0u &&
           (uint16_t)y+8u<=last && (uint16_t)y+8u<=end &&
           (y&63u)<=56u) {
            uint16_t entry=ray_codegen_handlers[depth[c]][(uint8_t)(y-t)>>3];
            if(entry) {
                ray_codegen_target=entry;
                ray_codegen_variant=(uint8_t)((wall_style[c]<<4)|u);
                uint16_t address=RAY_BAT_ADDRESS(y,pair);
                pce_cpu_irq_disable();
#if RAY_CODEGEN_FAST_SETUP
                ray_codegen_vram_address=address;
                ray_codegen_emit();
#else
                pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,address);
                *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
                ray_codegen_emit_legacy();
#endif
                pce_cpu_irq_enable();
                ray_codegen_words=(uint16_t)(ray_codegen_words+8u);
                ray_bat_words=(uint16_t)(ray_bat_words+8u);

                tex+=4u;
                y=(uint8_t)(y+8u);
                continue;
            }
        }
#endif
        uint8_t n=0;
        uint8_t stop=(uint8_t)((y&64u)?128u:64u);
        uint16_t *out=column_words;
        uint8_t yy=y;
        while(n<RAY_COLUMN_CHUNK_WORDS && yy<last && yy<stop) {
            if(yy>=t && yy<end) {
                *out++=(uint16_t)(0xf200u|wall[*tex]);
                if(texphase)++tex;
                texphase^=1u;
            } else *out++=ray_backdrop_row(yy)[pair];
            ++n;
            ++yy;
#if RAY_WALL_CODEGEN
            /* Stop the scalar prefix exactly at the next generated
             * eight-row span. Otherwise a displaced old wall top makes
             * every later batch misaligned and bypasses all microcode. */
            if(yy>=t && yy<end && ((uint8_t)(yy-t)&7u)==0u)break;
#endif
        }
        uint16_t addr=RAY_BAT_ADDRESS(y,pair);
        pce_cpu_irq_disable();
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,addr);
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
#if RAY_COLUMN_TIA
        pce_memop((void*)IO_VDC_DATA,column_words,(uint16_t)(n<<1),PCE_MEMOP_INCR_ALT);
#else
        for(uint8_t j=0;j<n;++j)*IO_VDC_DATA=column_words[j];
#endif
        pce_cpu_irq_enable();
        ray_bat_words=(uint16_t)(ray_bat_words+n);
        y=yy;
    }
}
static void render_columns(void) {
    if(next_column==0u) {
        if(cast_valid && cast_angle==angle &&
           cast_x==world_x && cast_y==world_y)return;
        cast_x=world_x;cast_y=world_y;cast_angle=angle;cast_valid=1u;
        cast_scene();
        column_pass_dirty=0;
    }
    for(uint8_t i=0;i<RAY_COLUMNS_PER_UPDATE;++i) {
        uint8_t c=(uint8_t)(next_column+i);
        uint8_t t=top[c],height=wall_height[depth[c]];
        uint8_t u=(uint8_t)(tex_u[c]&RAY_U_MASK);
        if(old_height[c]!=0 && old_top[c]==t && old_height[c]==height &&
           old_tex[c]==u && old_style[c]==wall_style[c] && old_depth[c]==depth[c])continue;
        uint8_t first=t,last=(uint8_t)(t+height);
        if(old_height[c]) {
            if(old_top[c]<first)first=old_top[c];
            uint8_t old_last=(uint8_t)(old_top[c]+old_height[c]);
            if(old_last>last)last=old_last;
        }
        column_pass_dirty=1u;
        column_upload((uint8_t)(c<<1),first,last,c,u);
        column_upload((uint8_t)((c<<1)+1u),first,last,c,(uint8_t)((u+2u)&RAY_U_MASK));
        old_top[c]=t;old_height[c]=height;old_tex[c]=u;old_style[c]=wall_style[c];old_depth[c]=depth[c];
    }
    next_column=(uint8_t)((next_column+RAY_COLUMNS_PER_UPDATE)&31u);
    if(next_column==0u && column_pass_dirty)++ray_redraws;
}
#endif
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
#if RAY_DOUBLE_BUFFER
    bat_bitmap_setup(colors);
#else
    bat_bitmap_setup(ray_sheet_palette);
#endif
    world_x=3*256+128;world_y=3*256+128;angle=0;
#if RAY_COLUMN_STREAM
    column_background_init();
#endif
    bat_bitmap_display();
#if RAY_COLUMN_STREAM
    /* BAT row increment is now 128: one VRAM stream is one screen column. */
    pce_cpu_irq_disable();
    pce_vdc_poke(VDC_REG_CONTROL,VDC_CONTROL_ENABLE_BG|
                 VDC_CONTROL_IRQ_SCANLINE|VDC_CONTROL_IRQ_VBLANK|
                 VDC_CONTROL_VRAM_ADD_128);
    pce_cpu_irq_enable();
    next_column=0;cast_valid=0;ray_bat_words=0;
#if RAY_WALL_CODEGEN
    ray_codegen_words=0;
#endif
    for(uint8_t c=0;c<32;++c)old_height[c]=0;
#endif
    draw_row=0;ray_redraws=0;
#if RAY_DOUBLE_BUFFER
    draw_page=1u;
#endif
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
#if RAY_COLUMN_STREAM
        render_columns();
#else
        render_slice();
#endif
        publish(frame,buttons,world_x-old_x,world_y-old_y);++frame;
    }
}
