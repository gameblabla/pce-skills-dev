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
#include "hires_texels.h"
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
/* 128 independently directed rays; two pixels packed into each of 64 BAT words. */
static uint8_t depth[128],top[128],tex_u[128],wall_kind[128];
/* Fourteen pre-quantized source-sheet material/shade classes in full detail. */
static uint8_t wall_style[128];
/* The exact hit cell guards interpolation across occlusion boundaries. */
static uint8_t ray_hit_cell[128];
static uint8_t ray_tex_phase[128];
#ifndef RAY_ADAPTIVE_RAYS
#define RAY_ADAPTIVE_RAYS 2
#endif
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
/* Limit the number of distinct BAT pairs scheduled per VBlank. Work on a
 * long wall column is resumable across VBlanks below. */
#define RAY_COLUMNS_PER_UPDATE 2u
#endif
#ifndef RAY_COLUMN_CHUNK_WORDS
#define RAY_COLUMN_CHUNK_WORDS 8u
#endif
#ifndef RAY_HIRES_MAX_DEPTH
#define RAY_HIRES_MAX_DEPTH 8u
#endif
#ifndef RAY_STAGE_UPLOAD
#define RAY_STAGE_UPLOAD 0
#endif
#ifndef RAY_VBLANK_WORD_BUDGET
/* Staging computes complex wall pixels before VBlank, so larger transfers
 * can be safely issued as separate <=8-word TIA bursts. The historical
 * in-VBlank renderer retains its conservative 24-word limit. */
#if RAY_STAGE_UPLOAD
#define RAY_VBLANK_WORD_BUDGET 96u
#else
#define RAY_VBLANK_WORD_BUDGET 24u
#endif
#endif
static uint8_t next_column,cast_valid,cast_angle;
static volatile uint8_t column_pairs_per_update;
static uint8_t upload_active,upload_next_y,upload_last_y;
static int16_t cast_x,cast_y;
/* The raster image is determined by wall height, horizontal texture phase
 * and material/shade. Two ray depths with equal heights share the same
 * generated V-table, so depth itself is NOT part of the visual dirty key.
 * Keep RAY_CANONICAL_WALL_KEY=0 for same-source reference comparisons. */
#ifndef RAY_CANONICAL_WALL_KEY
#define RAY_CANONICAL_WALL_KEY 1
#endif
static uint8_t old_top[128],old_height[128],old_tex[128],old_style[128];
#if !RAY_CANONICAL_WALL_KEY
static uint8_t old_depth[128];
#endif
static uint8_t column_pass_dirty;
volatile uint16_t ray_bat_words;
/* Irregular spans are at most eight BAT words (16 bytes). On measured
 * HuC6280 builds, direct VDC writes beat TIA setup for these short tails;
 * generated full eight-word blocks remain the preferred fast path. Set
 * RAY_COLUMN_TIA=1 to reproduce the previous implementation. */
#ifndef RAY_COLUMN_TIA
#define RAY_COLUMN_TIA 0
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
volatile uint8_t ray_codegen_variant_right;
volatile uint8_t ray_codegen_low_nibble;
/* The generated native texture table is V-major; share it with short
 * scalar tails instead of linking a second 3.5 KiB transposed copy. */
extern const uint8_t ray_codegen_pixels[16][224];
static const uint8_t *const ray_codegen_vlines[16]={
    ray_codegen_pixels[0],ray_codegen_pixels[1],ray_codegen_pixels[2],ray_codegen_pixels[3],
    ray_codegen_pixels[4],ray_codegen_pixels[5],ray_codegen_pixels[6],ray_codegen_pixels[7],
    ray_codegen_pixels[8],ray_codegen_pixels[9],ray_codegen_pixels[10],ray_codegen_pixels[11],
    ray_codegen_pixels[12],ray_codegen_pixels[13],ray_codegen_pixels[14],ray_codegen_pixels[15]
};
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
    uint8_t tx=(uint8_t)(((uint16_t)x)>>8);
    uint8_t ty=(uint8_t)(((uint16_t)y)>>8);
    if(tx>=8u||ty>=8u)return 1;
    return map[ty][tx];
}
static uint8_t cast_ray(uint8_t col) {
    int8_t dx=ray_step_x[angle&7u][col],dy=ray_step_y[angle&7u][col];
    if(angle&8u){dx=(int8_t)-dx;dy=(int8_t)-dy;}
    int16_t x=world_x,y=world_y;
    for(uint8_t n=1;n<=32;++n) {
        int16_t px=x,py=y;
        x+=dx;y+=dy;
        /* No grid boundary crossed: the next cell is necessarily empty.
         * Avoid a map lookup on almost every sub-cell march. */
        if(((uint16_t)px>>8)==((uint16_t)x>>8) &&
           ((uint16_t)py>>8)==((uint16_t)y>>8))continue;
        uint8_t m=material_at(x,y);
        if(m) {
            /* One sub-cell midpoint refinement locates the first solid cell within
             * the last ray step. Do not sample the texture at the overshot
             * marching endpoint (which makes textures jump on rotation). */
            {
                int16_t mx=(int16_t)(px+((x-px)>>1));
                int16_t my=(int16_t)(py+((y-py)>>1));
                if(material_at(mx,my)) {x=mx;y=my;}
                else {px=mx;py=my;}
            }
            ray_tex_phase[col]=(uint8_t)((((uint16_t)px>>8)!=((uint16_t)x>>8))?y:x);
            tex_u[col]=ray_tex_phase[col]>>4;
            if(((uint16_t)px>>8)!=((uint16_t)x>>8))m|=0x80u;
            wall_kind[col]=m;
            ray_hit_cell[col]=(uint8_t)((((uint8_t)(((uint16_t)y)>>8))<<3) | (uint8_t)(((uint16_t)x)>>8));
            return n;
        }
    }
    tex_u[col]=0;ray_tex_phase[col]=0;wall_kind[col]=1;ray_hit_cell[col]=0xffu;
    return 32;
}

/* Conservative NES-style sparse ray refinement. Source directions remain
 * 128 entries; only flat same-cell regions are interpolated. All wall edges
 * and texture-phase discontinuities are cast at their exact sample angle. */
#if RAY_ADAPTIVE_RAYS
static void cast_or_interpolate(uint8_t c,uint8_t l,uint8_t r) {
    if(ray_hit_cell[l]!=ray_hit_cell[r] ||
       wall_kind[l]!=wall_kind[r] ||
       (depth[l]>depth[r]+3u) || (depth[r]>depth[l]+3u)) {
        depth[c]=cast_ray(c);return;
    }
    uint8_t ul=tex_u[l],ur=tex_u[r];
    if((ul<=3u && ur>=12u) || (ur<=3u && ul>=12u)) {
        depth[c]=cast_ray(c);return;
    }
    int8_t du=(int8_t)(ur-ul);
    if(du>8)du-=16;
    if(du< -8)du+=16;
    if(du< -4 || du>4) {
        depth[c]=cast_ray(c);return;
    }
    depth[c]=(uint8_t)((depth[l]+depth[r]+1u)>>1);
    ray_tex_phase[c]=(uint8_t)(((uint16_t)ray_tex_phase[l]+ray_tex_phase[r]+1u)>>1);
    tex_u[c]=ray_tex_phase[c]>>4;
    wall_kind[c]=wall_kind[l];
    ray_hit_cell[c]=ray_hit_cell[l];
}
#endif
__attribute__((noinline)) static void cast_scene(void) {
    near_depth=0xffff;far_depth=0;hit_count=0;
#if RAY_ADAPTIVE_RAYS == 2
    /* Four-sample anchors, then exact edges and two refinement levels.
     * Explicit last two rays prevent reading past the 128-element table. */
    for(uint8_t c=0;c<128;c+=4u)depth[c]=cast_ray(c);
    depth[126]=cast_ray(126u);
    depth[127]=cast_ray(127u);
    for(uint8_t c=2;c<126;c+=4u)cast_or_interpolate(c,c-2u,c+2u);
    for(uint8_t c=1;c<127;c+=2u)cast_or_interpolate(c,c-1u,c+1u);
#elif RAY_ADAPTIVE_RAYS == 1
    for(uint8_t c=0;c<128;c+=2u)depth[c]=cast_ray(c);
    for(uint8_t c=1;c<127;c+=2u)cast_or_interpolate(c,c-1u,c+1u);
    depth[127]=cast_ray(127u);
#else
    for(uint8_t c=0;c<128;++c)depth[c]=cast_ray(c);
#endif
    for(uint8_t c=0;c<128;++c) {
        uint8_t d=depth[c];
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
    const uint8_t l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
    const uint8_t lt=top[l],rt=top[r],ld=depth[l],rd=depth[r];
    const uint8_t left_wall=(uint8_t)(y>=lt && (uint8_t)(y-lt)<wall_height[ld]);
    const uint8_t right_wall=(uint8_t)(y>=rt && (uint8_t)(y-rt)<wall_height[rd]);
    uint8_t result;
    /* Do not calculate a perspective floor (or the sky) behind two wall
     * pixels. The atomic page is a CPU-bound alternative to column mode. */
    if(left_wall && right_wall) {
#if RAY_WALL_LOOKUP
        uint8_t lval=RAY_ACTIVE_PAIRS[wall_style[l]][tex_u[l]&RAY_U_MASK]
            [wall_tex_v[ld][(uint8_t)(y-lt)>>1]];
        uint8_t rval=RAY_ACTIVE_PAIRS[wall_style[r]][tex_u[r]&RAY_U_MASK]
            [wall_tex_v[rd][(uint8_t)(y-rt)>>1]];
        return (uint8_t)((lval&0xf0u)|(rval>>4));
#else
        return (uint8_t)((wall_pixel(l,tex_u[l]&RAY_U_MASK,y)<<4)|
               wall_pixel(r,tex_u[r]&RAY_U_MASK,y));
#endif
    }
    if(y<64u) {
        uint8_t sky=y<16u?0u:y<32u?1u:y<48u?2u:3u;
        result=(uint8_t)((sky<<4)|sky);
    } else {
        uint8_t fu,fv,delta;
        switch(floor_shift[y]) {
            case 4:fu=(uint8_t)(pair<<4);fv=(uint8_t)(y<<4);delta=8;break;
            case 3:fu=(uint8_t)(pair<<3);fv=(uint8_t)(y<<3);delta=4;break;
            case 2:fu=(uint8_t)(pair<<2);fv=(uint8_t)(y<<2);delta=2;break;
            case 1:fu=(uint8_t)(pair<<1);fv=(uint8_t)(y<<1);delta=1;break;
            default:fu=pair;fv=y;delta=1;break;
        }
        fu=(uint8_t)(fu+(uint8_t)(render_world_x>>5));
        fv=(uint8_t)(fv+(uint8_t)(render_world_y>>5));
        result=(uint8_t)((floor_color(fu,fv)<<4)|floor_color((uint8_t)(fu+delta),fv));
    }
    if(left_wall) {
#if RAY_WALL_LOOKUP
        uint8_t pix=RAY_ACTIVE_PAIRS[wall_style[l]][tex_u[l]&RAY_U_MASK]
            [wall_tex_v[ld][(uint8_t)(y-lt)>>1]];
        result=(uint8_t)((result&0x0fu)|(pix&0xf0u));
#else
        result=(uint8_t)((result&0x0fu)|
                   (wall_pixel(l,tex_u[l]&RAY_U_MASK,y)<<4));
#endif
    }
    if(right_wall) {
#if RAY_WALL_LOOKUP
        uint8_t pix=RAY_ACTIVE_PAIRS[wall_style[r]][tex_u[r]&RAY_U_MASK]
            [wall_tex_v[rd][(uint8_t)(y-rt)>>1]];
        result=(uint8_t)((result&0xf0u)|(pix>>4));
#else
        result=(uint8_t)((result&0xf0u)|wall_pixel(r,tex_u[r]&RAY_U_MASK,y));
#endif
    }
    return result;
}

/* Build a bounded RAM staging batch, then transfer BAT entries ONLY in VBlank.
 * Each TIA sends a bounded row burst to alternating VDC data ports
 * ($0002/$0003), autoincrementing the VRAM word address. TIA masks IRQs
 * until completion; no raster event is needed during that brief mask.
 * Unsupported larger batches have NOT been validated on hardware.
 * Cache camera position once per 128-row redraw so its textured floor never
 * combines pixels from multiple player positions inside the same pass.
 */
static __attribute__((unused)) void render_slice(void) {
    if(draw_row==0u) {
        render_world_x=world_x;render_world_y=world_y;
        cast_scene();
    }
    for(uint8_t i=0;i<RAY_SLICE_ROWS;++i) {
        uint8_t y=(uint8_t)(draw_row+i);
#if RAY_DOUBLE_BUFFER
        /* Vertical 2:1 downsampling buys the second BAT page. */
        y=(uint8_t)(y<<1);
#endif
        for(uint8_t pair=0;pair<64u;++pair)
            scan_words[i][pair]=(uint16_t)(0xf200u|bitmap_pair(pair,y));
    }
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
static uint16_t backdrop_init_row[64];
static void column_background_init(void) {
    for(uint8_t y=0;y<128u;++y) {
        uint16_t addr=(uint16_t)((((uint16_t)y&63u)<<7)+((y&64u)?64u:0u));
#if RAY_BAT_ADDRESS_LUT
        ray_bat_addresses[y]=addr;
#endif
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,addr);
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
        /* Generate once, then upload full BAT rows with VDC display off. */
        for(uint8_t p=0;p<64u;++p)backdrop_init_row[p]=ray_backdrop_word(y,p);
        pce_memop((void*)IO_VDC_DATA,backdrop_init_row,128u,PCE_MEMOP_INCR_ALT);
    }
}
/* Word renderer: two genuinely different 128-ray samples, with a fast
 * paired-texel shortcut only where both projected lanes exactly agree.
 * Generated eight-row native writer remains valid for those common cases;
 * other rows compose the two 4-bit pixels without updating pattern VRAM. */
static __attribute__((unused)) uint8_t ray_pair_fast(uint8_t left,uint8_t right) {
    /* Both pixels share height and V phase, but can have different textures,
     * U coordinates, shading and material. The native writer fuses them. */
    return (uint8_t)(top[left]==top[right] &&
        wall_height[depth[left]]==wall_height[depth[right]]);
}
static __attribute__((unused)) void column_upload(uint8_t pair,uint8_t first,uint8_t last) {
    const uint8_t l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
    const uint8_t tl=top[l],tr=top[r];
    const uint8_t el=(uint8_t)(tl+wall_height[depth[l]]);
    const uint8_t er=(uint8_t)(tr+wall_height[depth[r]]);
#if !RAY_WALL_CODEGEN
    const uint8_t *wl=RAY_ACTIVE_PAIRS[wall_style[l]][tex_u[l]&RAY_U_MASK];
    const uint8_t *wr=RAY_ACTIVE_PAIRS[wall_style[r]][tex_u[r]&RAY_U_MASK];
#endif
/* Full source texture resolution for close walls: 32 distinct V samples
     * and correct shade. The native 16-row writer remains fast for far walls. */
    const uint8_t detailed_l=depth[l]<=RAY_HIRES_MAX_DEPTH,detailed_r=depth[r]<=RAY_HIRES_MAX_DEPTH;
    const uint8_t *vl=wall_tex_v[depth[l]],*vr=wall_tex_v[depth[r]];
#if RAY_WALL_CODEGEN
    const uint8_t fast=(uint8_t)(!detailed_l && !detailed_r && ray_pair_fast(l,r));
#endif
    for(uint8_t y=first;y<last;) {
#if RAY_WALL_CODEGEN
        if(fast && y>=tl && (uint8_t)(y-tl)%8u==0u &&
           (uint16_t)y+8u<=last && (uint16_t)y+8u<=el &&
           (y&63u)<=56u) {
            uint16_t entry=ray_codegen_handlers[depth[l]][(uint8_t)(y-tl)>>3];
            if(entry) {
                ray_codegen_target=entry;
                ray_codegen_variant=(uint8_t)((wall_style[l]<<4)|(tex_u[l]&RAY_U_MASK));
                ray_codegen_variant_right=(uint8_t)((wall_style[r]<<4)|((tex_u[r]-1u)&RAY_U_MASK));
                ray_codegen_vram_address=RAY_BAT_ADDRESS(y,pair);
                pce_cpu_irq_disable();
#if RAY_CODEGEN_FAST_SETUP
                ray_codegen_emit();
#else
                pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,ray_codegen_vram_address);
                *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
                ray_codegen_emit_legacy();
#endif
                pce_cpu_irq_enable();
                ray_codegen_words=(uint16_t)(ray_codegen_words+8u);
                ray_bat_words=(uint16_t)(ray_bat_words+8u);
                y=(uint8_t)(y+8u);
                continue;
            }
        }
#endif
        uint8_t n=0,stop=(uint8_t)((y&64u)?128u:64u),yy=y;
        uint16_t *out=column_words;
        while(n<RAY_COLUMN_CHUNK_WORDS && yy<last && yy<stop) {
            uint16_t word=ray_backdrop_word(yy,pair);
            if(yy>=tl && yy<el) {
                uint8_t pixel;
                if(detailed_l) {
                    uint8_t v=ray_hires_v[depth[l]][(uint8_t)(yy-tl)];
                    uint8_t both=ray_wall_hires[wall_style[l]>>1][ray_tex_phase[l]>>3][v>>1];
                    pixel=(uint8_t)((v&1u)?(both&15u):(both>>4));
                    if(wall_style[l]&1u)pixel=ray_hires_dark[pixel];
                } else {
#if RAY_WALL_CODEGEN
                    pixel=(uint8_t)(ray_codegen_vlines[vl[(uint8_t)(yy-tl)>>1]]
                        [(wall_style[l]<<4)|(tex_u[l]&15u)]>>4);
#else
                    pixel=(uint8_t)(wl[vl[(uint8_t)(yy-tl)>>1]]>>4);
#endif
                }
                word=(uint16_t)((word&0xff0fu)|((uint16_t)pixel<<4));
            }
            if(yy>=tr && yy<er) {
                uint8_t pixel;
                if(detailed_r) {
                    uint8_t v=ray_hires_v[depth[r]][(uint8_t)(yy-tr)];
                    uint8_t both=ray_wall_hires[wall_style[r]>>1][ray_tex_phase[r]>>3][v>>1];
                    pixel=(uint8_t)((v&1u)?(both&15u):(both>>4));
                    if(wall_style[r]&1u)pixel=ray_hires_dark[pixel];
                } else {
#if RAY_WALL_CODEGEN
                    pixel=(uint8_t)(ray_codegen_vlines[vr[(uint8_t)(yy-tr)>>1]]
                        [(wall_style[r]<<4)|((tex_u[r]-1u)&15u)]&15u);
#else
                    pixel=(uint8_t)(wr[vr[(uint8_t)(yy-tr)>>1]]>>4);
#endif
                }
                word=(uint16_t)((word&0xfff0u)|pixel);
            }
            *out++=word;
            ++n;++yy;
#if RAY_WALL_CODEGEN
            if(fast && yy>=tl && yy<el && ((uint8_t)(yy-tl)&7u)==0u)break;
#endif
        }
        pce_cpu_irq_disable();
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,RAY_BAT_ADDRESS(y,pair));
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
static uint8_t column_prepare(void) {
    /* Do not recast or replace current wall samples halfway through an
     * interrupted vertical column. It must be completed first. */
    if(upload_active)return 1u;
    if(next_column==0u) {
        if(cast_valid && cast_angle==angle &&
           cast_x==world_x && cast_y==world_y)return 0u;
        cast_x=world_x;cast_y=world_y;cast_angle=angle;cast_valid=1u;
        cast_scene();column_pass_dirty=0;
    }
    return 1u;
}
static void finish_column(uint8_t pair) {
    const uint8_t l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
    for(uint8_t c=l;c<=r;++c) {
        old_top[c]=top[c];old_height[c]=wall_height[depth[c]];
        old_tex[c]=(uint8_t)(depth[c]<=RAY_HIRES_MAX_DEPTH?(ray_tex_phase[c]>>3):
                           (tex_u[c]&RAY_U_MASK));old_style[c]=wall_style[c];
#if !RAY_CANONICAL_WALL_KEY
        old_depth[c]=depth[c];
#endif
    }
    next_column=(uint8_t)((pair+1u)&63u);
    if(next_column==0u && column_pass_dirty)++ray_redraws;
}
#if !RAY_STAGE_UPLOAD
static void render_columns(void) {
    uint8_t budget=RAY_VBLANK_WORD_BUDGET;
    for(uint8_t i=0;i<column_pairs_per_update && budget;++i) {
        /* Reaching zero commits this view: never begin the next camera
         * pass in the same VBlank without a fresh projection. */
        if(i && next_column==0u)break;
        const uint8_t pair=next_column,l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
        if(!upload_active) {
            uint8_t dirty=0,first=128u,last=0u;
            for(uint8_t c=l;c<=r;++c) {
                const uint8_t h=wall_height[depth[c]], t=top[c];
                if(old_height[c]!=h || old_top[c]!=t ||
                   old_tex[c]!=(depth[c]<=RAY_HIRES_MAX_DEPTH?(ray_tex_phase[c]>>3):
                                (tex_u[c]&RAY_U_MASK)) ||
                   old_style[c]!=wall_style[c]
#if !RAY_CANONICAL_WALL_KEY
                   || old_depth[c]!=depth[c]
#endif
                  ) {
                    dirty=1u;
                    if(t<first)first=t;
                    if((uint8_t)(t+h)>last)last=(uint8_t)(t+h);
                    if(old_top[c]<first && old_height[c])first=old_top[c];
                    uint8_t end=(uint8_t)(old_top[c]+old_height[c]);
                    if(end>last)last=end;
                }
            }
            if(!dirty) {finish_column(pair);continue;}
            upload_next_y=first;upload_last_y=last;upload_active=1u;
            column_pass_dirty=1u;
        }
        /* This bounded segment may stop mid-column. The next VBlank
         * continues at upload_next_y, rather than losing the wall suffix
         * or falsely marking the pair clean. */
        const uint8_t remain=(uint8_t)(upload_last_y-upload_next_y);
        const uint8_t n=remain<budget?remain:budget;
        column_upload(pair,upload_next_y,(uint8_t)(upload_next_y+n));
        upload_next_y=(uint8_t)(upload_next_y+n);
        budget=(uint8_t)(budget-n);
        if(upload_next_y!=upload_last_y)break;
        upload_active=0u;
        finish_column(pair);
    }
}
#else
/* Drawing and VRAM presentation are two distinct phases. The heavier 32x32
 * textured pixels are calculated before VBlank; while the display is active,
 * only a tiny buffered TIA burst with bounded IRQ masking touches VDC DATA.
 * This prevents missed raster IRQs without lowering the uploaded detail. */
static uint16_t staged_words[RAY_VBLANK_WORD_BUDGET];
static uint8_t staged_ready,staged_pair,staged_first,staged_count;

static uint16_t stage_word(uint8_t pair,uint8_t y) {
    uint8_t l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
    uint8_t tl=top[l],tr=top[r];
    uint16_t w=ray_backdrop_word(y,pair);
    if(y>=tl && (uint8_t)(y-tl)<wall_height[depth[l]]) {
        uint8_t pixel;
        if(depth[l]<=RAY_HIRES_MAX_DEPTH) {
            uint8_t v=ray_hires_v[depth[l]][(uint8_t)(y-tl)];
            uint8_t both=ray_wall_hires[wall_style[l]>>1][ray_tex_phase[l]>>3][v>>1];
            pixel=(uint8_t)((v&1u)?(both&15u):(both>>4));
            if(wall_style[l]&1u)pixel=ray_hires_dark[pixel];
        } else {
            uint8_t v=wall_tex_v[depth[l]][(uint8_t)(y-tl)>>1];
            pixel=(uint8_t)(ray_sheet_pairs[wall_style[l]][tex_u[l]&15u][v]>>4);
        }
        w=(uint16_t)((w&0xff0fu)|((uint16_t)pixel<<4));
    }
    if(y>=tr && (uint8_t)(y-tr)<wall_height[depth[r]]) {
        uint8_t pixel;
        if(depth[r]<=RAY_HIRES_MAX_DEPTH) {
            uint8_t v=ray_hires_v[depth[r]][(uint8_t)(y-tr)];
            uint8_t both=ray_wall_hires[wall_style[r]>>1][ray_tex_phase[r]>>3][v>>1];
            pixel=(uint8_t)((v&1u)?(both&15u):(both>>4));
            if(wall_style[r]&1u)pixel=ray_hires_dark[pixel];
        } else {
            uint8_t v=wall_tex_v[depth[r]][(uint8_t)(y-tr)>>1];
            pixel=(uint8_t)(ray_sheet_pairs[wall_style[r]][tex_u[r]&15u][v]>>4);
        }
        w=(uint16_t)((w&0xfff0u)|pixel);
    }
    return w;
}

static void stage_columns(void) {
    staged_ready=0u;
    /* Skip any unchanged columns, but never start the next view with stale
     * samples after finishing pair 63. Last-pass commits happen only after
     * all of their actual VRAM uploads are acknowledged. */
    for(uint8_t checked=0;checked<64u;++checked) {
        if(checked && next_column==0u)return;
        uint8_t pair=next_column,l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
        if(!upload_active) {
            uint8_t dirty=0,first=128u,last=0u;
            for(uint8_t c=l;c<=r;++c) {
                uint8_t h=wall_height[depth[c]],t=top[c];
                if(old_height[c]!=h || old_top[c]!=t ||
                   old_tex[c]!=(depth[c]<=RAY_HIRES_MAX_DEPTH?
                             (ray_tex_phase[c]>>3):(tex_u[c]&RAY_U_MASK)) ||
                   old_style[c]!=wall_style[c]
#if !RAY_CANONICAL_WALL_KEY
                   || old_depth[c]!=depth[c]
#endif
                  ) {
                    dirty=1u;
                    if(t<first)first=t;
                    if((uint8_t)(t+h)>last)last=(uint8_t)(t+h);
                    if(old_top[c]<first && old_height[c])first=old_top[c];
                    uint8_t end=(uint8_t)(old_top[c]+old_height[c]);
                    if(end>last)last=end;
                }
            }
            if(!dirty) {finish_column(pair);continue;}
            upload_next_y=first;upload_last_y=last;
            upload_active=1u;column_pass_dirty=1u;
        }
        uint8_t remaining=(uint8_t)(upload_last_y-upload_next_y);
        staged_count=(remaining<RAY_VBLANK_WORD_BUDGET)?remaining:RAY_VBLANK_WORD_BUDGET;
        staged_first=upload_next_y;staged_pair=pair;
        for(uint8_t j=0;j<staged_count;++j)
            staged_words[j]=stage_word(pair,(uint8_t)(staged_first+j));
        staged_ready=1u;
        return;
    }
}

static void render_columns(void) {
    if(!staged_ready)return;
    uint8_t done=0u;
    while(done<staged_count) {
        uint8_t y=(uint8_t)(staged_first+done);
        uint8_t n=(uint8_t)(staged_count-done);
        uint8_t until_page=(uint8_t)(64u-(y&63u));
        if(n>8u)n=8u;
        if(n>until_page)n=until_page;
        pce_cpu_irq_disable();
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,RAY_BAT_ADDRESS(y,staged_pair));
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
        pce_memop((void*)IO_VDC_DATA,staged_words+done,(uint16_t)(n<<1),PCE_MEMOP_INCR_ALT);
        pce_cpu_irq_enable();
        done=(uint8_t)(done+n);
    }
    ray_bat_words=(uint16_t)(ray_bat_words+staged_count);
    upload_next_y=(uint8_t)(upload_next_y+staged_count);
    if(upload_next_y==upload_last_y) {
        upload_active=0u;
        finish_column(staged_pair);
    }
    staged_ready=0u;
}
#endif
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
    t->state[0]=128;t->state[1]=hit_count;
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
    next_column=0;cast_valid=0;upload_active=0;ray_bat_words=0;
    column_pairs_per_update=RAY_COLUMNS_PER_UPDATE;
#if RAY_WALL_CODEGEN
    ray_codegen_words=0;
#endif
    for(uint8_t c=0;c<128;++c)old_height[c]=0;
#endif
    draw_row=0;ray_redraws=0;
#if RAY_DOUBLE_BUFFER
    draw_page=1u;
#endif
    uint32_t frame=0;
    for(;;) {
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
        /* Project in active raster time; VDC BAT writes only after VBlank. */
        uint8_t pending=column_prepare();
#if RAY_STAGE_UPLOAD
        if(pending)stage_columns();
#endif
        uint8_t before=bat_frames;while(before==bat_frames){}
        if(pending) render_columns();
#else
        uint8_t before=bat_frames;while(before==bat_frames){}
        render_slice();
#endif
        publish(frame,buttons,world_x-old_x,world_y-old_y);++frame;
    }
}
