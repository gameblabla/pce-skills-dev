/* Example implementation. Not speed optimized, has issues.
 * Wolf3D-style 2.5D raycaster rendered through PCEdev's 512x224
 * paired-BAT pseudo-bitmap: 128x128 logical pixels, two 4-bit pixels per BAT
 * word, 256 permanent patterns. NO per-frame planar tile uploads.
 * Rays, wall geometry, textures, ceiling and floor are all drawn as pixels.
 * LEFT/RIGHT turn, UP/DOWN walk, with independent solid-cell collision.
 */
#include <pce.h>
#include <stdint.h>
#include "genre_trace.h"
#include "ray_tables.h"
#include "wall_pairs.h"
#include "sheet_pairs.h"
#include "hires_texels.h"
#include "sheet_palette.h"
#define RAY_ACTIVE_PAIRS ray_sheet_pairs
#define RAY_U_MASK 15u
#ifndef RAY_FAST_SPANS
#define RAY_FAST_SPANS 1
#endif
#if RAY_FAST_SPANS
#include "backdrop_words.h"
#if RAY_BACKDROP_LUT
#define RAY_BACKDROP_FAST_WORD(y,p) ray_backdrop_lut_word((y),(p))
#else
#define RAY_BACKDROP_FAST_WORD(y,p) ray_backdrop_word((y),(p))
#endif
#endif
#include "bat_bitmap.h"
#define RAY_LOGICAL_ROWS 128u
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
/* The second BAT page is circularly shifted by one physical BAT row.
 * At the 64/65 raster seam the VDC temporarily retains the previous BYR;
 * both halves must therefore use BAT row 63 for logical y=63/64. */
#define RAY_BAT_ADDRESS(y,pair) ((uint16_t)((((uint16_t)(((y)&64u)?(((y)-1u)&63u):((y)&63u)))<<7)+(((y)&64u)?64u:0u)+(pair)))
#endif
/* A progressive pass need not expose the stale center of the image until
 * the uploader reaches column 32. Work from the player's view center out:
 * 31,32,30,33,...,0,63. Every pair is still visited exactly once; this
 * changes latency, not resolution, image quality, or the VBlank word cap. */
#ifndef RAY_CENTER_FIRST
#define RAY_CENTER_FIRST 1
#endif
#if RAY_CENTER_FIRST
#define RAY_FIRST_PAIR 31u
static uint8_t ray_next_pair(uint8_t pair) {
    if(pair==63u)return 31u;
    return (uint8_t)(pair<=31u?63u-pair:62u-pair);
}
#else
#define RAY_FIRST_PAIR 0u
static uint8_t ray_next_pair(uint8_t pair) {
    return (uint8_t)((pair+1u)&63u);
}
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
/* In column streams, the VDC automatically advances MAWR by 128 BAT
 * words per uploaded word. Preserve it across short IRQ-safe TIA bursts;
 * select DATA again after a raster IRQ rather than resetting MAWR each
 * time. Explicitly readdress at the BAT page/seam wrap. */
#ifndef RAY_PRESENT_CONTIGUOUS
#define RAY_PRESENT_CONTIGUOUS 1
#endif
/* Short staged BAT bursts use the HuC6280's immediate ST0 instruction,
 * avoiding a general-purpose SDK call in the raster-sensitive loop. */
#ifndef RAY_INLINE_VDC_ADDRESS
#define RAY_INLINE_VDC_ADDRESS 1
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

static uint8_t material_at(int16_t x,int16_t y) {
    uint8_t tx=(uint8_t)(((uint16_t)x)>>8);
    uint8_t ty=(uint8_t)(((uint16_t)y)>>8);
    if(tx>=8u||ty>=8u)return 1;
    return map[ty][tx];
}
/* VCS-style gridline tracking experiment. The default preserves the
 * measured production caster. RAY_GRID_CROSSING uses cached tile indices
 * and skips exact, provably empty two-step segments, never interpolating
 * through a crossing. Distances and texture phases match the reference. */
#ifndef RAY_GRID_CROSSING
#define RAY_GRID_CROSSING 0
#endif
static uint8_t cast_ray(uint8_t col) {
    int8_t dx=ray_step_x[angle&7u][col],dy=ray_step_y[angle&7u][col];
    if(angle&8u){dx=(int8_t)-dx;dy=(int8_t)-dy;}
    int16_t x=world_x,y=world_y;
#if RAY_GRID_CROSSING
    uint8_t cx=(uint8_t)((uint16_t)x>>8);
    uint8_t cy=(uint8_t)((uint16_t)y>>8);
#endif
    for(uint8_t n=1;n<=32;++n) {
#if RAY_GRID_CROSSING
        /* Two-step jump is safe only when BOTH endpoints are in the same
         * cell. With a monotone signed step, the midpoint must be too. */
        if(n<32u) {
            int16_t x2=(int16_t)(x+(int16_t)dx*2);
            int16_t y2=(int16_t)(y+(int16_t)dy*2);
            if((((uint16_t)(x^x2))&0xff00u)==0u &&
               (((uint16_t)(y^y2))&0xff00u)==0u) {
                x=x2;y=y2;n=(uint8_t)(n+1u);
                continue;
            }
        }
        x+=dx;y+=dy;
        uint8_t nx=(uint8_t)((uint16_t)x>>8);
        uint8_t ny=(uint8_t)((uint16_t)y>>8);
        if(cx==nx && cy==ny)continue;
        int16_t px=(int16_t)(x-dx),py=(int16_t)(y-dy);
#else
        int16_t px=x,py=y;
        x+=dx;y+=dy;
        /* No grid boundary crossed: the next cell is necessarily empty. */
        if(((uint16_t)px>>8)==((uint16_t)x>>8) &&
           ((uint16_t)py>>8)==((uint16_t)y>>8))continue;
#endif
        uint8_t m=material_at(x,y);
        if(m) {
            /* Midpoint refinement preserves the precise Q8 wall phase. */
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
#if RAY_GRID_CROSSING
        cx=nx;cy=ny;
#endif
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
        wall_style[c]=(uint8_t)((((material?material:1u)-1u)<<1) |
             ((d>16u || (wall_kind[c]&0x80u))?1u:0u));
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
     * pixels. This path is used for source-reference comparisons only. */
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
        uint16_t address=((uint16_t)(y&63u)<<7)+((y&64u)?64u:0u);
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
        ++ray_redraws;
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
        /* Rotate the second BAT half so its last row holds logical y=64.
         * The first page keeps the natural y=0..63 arrangement. */
        uint8_t bat_y=(uint8_t)((y&64u)?((y-1u)&63u):(y&63u));
        uint16_t addr=(uint16_t)(((uint16_t)bat_y<<7)+((y&64u)?64u:0u));
#if RAY_BAT_ADDRESS_LUT
        ray_bat_addresses[y]=addr;
#endif
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,addr);
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
        /* Generate once, then upload full BAT rows with VDC display off. */
        for(uint8_t p=0;p<64u;++p)backdrop_init_row[p]=RAY_BACKDROP_FAST_WORD(y,p);
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
           ((y&64u)?((y-1u)&63u):(y&63u))<=56u) {
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
        uint8_t n=0,stop=(uint8_t)(y<64u?64u:(y==64u?65u:128u)),yy=y;
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
    if(next_column==RAY_FIRST_PAIR) {
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
    next_column=ray_next_pair(pair);
    if(next_column==RAY_FIRST_PAIR && column_pass_dirty)++ray_redraws;
}
#if !RAY_STAGE_UPLOAD
static void render_columns(void) {
    uint8_t budget=RAY_VBLANK_WORD_BUDGET;
    for(uint8_t i=0;i<column_pairs_per_update && budget;++i) {
        /* Reaching zero commits this view: never begin the next camera
         * pass in the same VBlank without a fresh projection. */
        if(i && next_column==RAY_FIRST_PAIR)break;
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
static uint8_t staged_ready,staged_segments,staged_total_words;
static uint8_t staged_segment_pair[64],staged_segment_first[64],staged_segment_count[64];
static uint8_t staged_segment_last[64],staged_segment_finish[64];

/* The VCS raycaster converter walks between wall-height thresholds rather
 * than repeatedly classifying each output pixel. Adapt that concept to the
 * PCE's two independently textured pixels per 16-bit BAT word. Unlike VCS
 * playfield deltas, the result is still written through the paired-BAT VDC.
 * Original VCS concept: Guillaume Laudet, MIT, 2018 (see docs/vcs-port.md).
 */
#ifndef RAY_VCS_SPAN_CONVERTER
#define RAY_VCS_SPAN_CONVERTER 1
#endif
/* Resolve the texture strips once per BAT pair instead of repeating three-
 * dimensional ROM indexing for every written pixel. Only the generated BAT
 * words (not the VDC presentation schedule) change in this optimization. */
/* Preserve the stage function as a profiler symbol only for equal-work
 * native cycle comparisons; normal builds let LLVM-MOS optimize freely. */
#if defined(RAY_PROFILE_STAGE_WORDS) && RAY_PROFILE_STAGE_WORDS
__attribute__((noinline))
#endif
static void stage_pair_words(uint8_t pair,uint8_t first,uint8_t count,uint16_t *dest) {
    uint8_t l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
    uint8_t tl=top[l],tr=top[r],dl=depth[l],dr=depth[r];
    uint8_t hl=wall_height[dl],hr=wall_height[dr];
    uint8_t sl=wall_style[l],sr=wall_style[r];
    uint8_t detail_l=dl<=RAY_HIRES_MAX_DEPTH;
    uint8_t detail_r=dr<=RAY_HIRES_MAX_DEPTH;
    const uint8_t *vl=detail_l?ray_hires_v[dl]:wall_tex_v[dl];
    const uint8_t *vr=detail_r?ray_hires_v[dr]:wall_tex_v[dr];
    const uint8_t *wl=detail_l?ray_wall_hires[sl>>1][ray_tex_phase[l]>>3]:
                                  ray_sheet_pairs[sl][tex_u[l]&15u];
    const uint8_t *wr=detail_r?ray_wall_hires[sr>>1][ray_tex_phase[r]>>3]:
                                  ray_sheet_pairs[sr][tex_u[r]&15u];
#if RAY_VCS_SPAN_CONVERTER
#define RAY_STAGE_LEFT_TEXEL do { \
    uint8_t v=vl[detail_l?(uint8_t)(y-tl):((uint8_t)(y-tl)>>1)]; \
    uint8_t pixel; \
    if(detail_l) { \
    uint8_t both=wl[v>>1]; \
    pixel=(uint8_t)((v&1u)?(both&15u):(both>>4)); \
    if(sl&1u)pixel=ray_hires_dark[pixel]; \
    } else { \
    pixel=(uint8_t)(wl[v]>>4); \
    } \
    pixels=(uint8_t)((pixels&0x0fu)|(pixel<<4)); \
} while(0)
#define RAY_STAGE_RIGHT_TEXEL do { \
    uint8_t v=vr[detail_r?(uint8_t)(y-tr):((uint8_t)(y-tr)>>1)]; \
    uint8_t pixel; \
    if(detail_r) { \
    uint8_t both=wr[v>>1]; \
    pixel=(uint8_t)((v&1u)?(both&15u):(both>>4)); \
    if(sr&1u)pixel=ray_hires_dark[pixel]; \
    } else { \
    pixel=(uint8_t)(wr[v]>>4); \
    } \
    pixels=(uint8_t)((pixels&0xf0u)|pixel); \
} while(0)
    /* The source VCS renderer uses min/max wall heights to omit empty
     * playfield lines. Clip our two wall intervals into horizontal coverage
     * runs, so the per-pixel loop no longer tests wall visibility. */
    const uint8_t lbottom=(uint8_t)(tl+hl);
    const uint8_t rbottom=(uint8_t)(tr+hr);
    const uint8_t last=(uint8_t)(first+count);
    for(uint8_t y=first; y<last;) {
        uint8_t until=last;
        if(tl>y && tl<until)until=tl;
        if(lbottom>y && lbottom<until)until=lbottom;
        if(tr>y && tr<until)until=tr;
        if(rbottom>y && rbottom<until)until=rbottom;
        uint8_t coverage=(uint8_t)(((y>=tl && y<lbottom)?2u:0u)|
                                   ((y>=tr && y<rbottom)?1u:0u));
        switch(coverage) {
            case 0:
                for(;y<until;++y)
                    *dest++=(uint16_t)(0xf200u|(uint8_t)RAY_BACKDROP_FAST_WORD(y,pair));
                break;
            case 1:
                for(;y<until;++y) {
                    uint8_t pixels=(uint8_t)RAY_BACKDROP_FAST_WORD(y,pair);
                    RAY_STAGE_RIGHT_TEXEL;
                    *dest++=(uint16_t)(0xf200u|pixels);
                }
                break;
            case 2:
                for(;y<until;++y) {
                    uint8_t pixels=(uint8_t)RAY_BACKDROP_FAST_WORD(y,pair);
                    RAY_STAGE_LEFT_TEXEL;
                    *dest++=(uint16_t)(0xf200u|pixels);
                }
                break;
            default:
                for(;y<until;++y) {
                    uint8_t pixels=0u;
                    RAY_STAGE_LEFT_TEXEL;
                    RAY_STAGE_RIGHT_TEXEL;
                    *dest++=(uint16_t)(0xf200u|pixels);
                }
                break;
        }
    }
#undef RAY_STAGE_LEFT_TEXEL
#undef RAY_STAGE_RIGHT_TEXEL
#else
    for(uint8_t j=0;j<count;++j) {
        uint8_t y=(uint8_t)(first+j);
        uint8_t pixels=(uint8_t)RAY_BACKDROP_FAST_WORD(y,pair);
        if(y>=tl && (uint8_t)(y-tl)<hl) {
            uint8_t v=vl[detail_l?(uint8_t)(y-tl):((uint8_t)(y-tl)>>1)];
            uint8_t pixel;
            if(detail_l) {
                uint8_t both=wl[v>>1];
                pixel=(uint8_t)((v&1u)?(both&15u):(both>>4));
                if(sl&1u)pixel=ray_hires_dark[pixel];
            } else {
                pixel=(uint8_t)(wl[v]>>4);
            }
            pixels=(uint8_t)((pixels&0x0fu)|(pixel<<4));
        }
        if(y>=tr && (uint8_t)(y-tr)<hr) {
            uint8_t v=vr[detail_r?(uint8_t)(y-tr):((uint8_t)(y-tr)>>1)];
            uint8_t pixel;
            if(detail_r) {
                uint8_t both=wr[v>>1];
                pixel=(uint8_t)((v&1u)?(both&15u):(both>>4));
                if(sr&1u)pixel=ray_hires_dark[pixel];
            } else {
                pixel=(uint8_t)(wr[v]>>4);
            }
            pixels=(uint8_t)((pixels&0xf0u)|pixel);
        }
        dest[j]=(uint16_t)(0xf200u|pixels);
    }
#endif
}

static void stage_columns(void) {
    uint8_t budget=RAY_VBLANK_WORD_BUDGET;
    uint8_t total=0u,segments=0u;
    uint8_t pair_cursor=next_column;
    uint8_t local_active=upload_active;
    uint8_t local_next=upload_next_y;
    uint8_t local_last=upload_last_y;
    staged_ready=0u;
    /* Skip any unchanged columns, but never start the next view with stale
     * samples after finishing pair 63. Last-pass commits happen only after
     * all of their actual VRAM uploads are acknowledged. */
    for(uint8_t checked=0;checked<64u && budget; ++checked) {
        if(checked && pair_cursor==RAY_FIRST_PAIR)break;
        uint8_t pair=pair_cursor,l=(uint8_t)(pair<<1),r=(uint8_t)(l+1u);
        if(!local_active) {
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
            if(!dirty) {
                /* A clean pair consumes no VRAM budget; defer its state
                 * acknowledgment until previously staged writes complete. */
                staged_segment_pair[segments]=pair;
                staged_segment_first[segments]=0u;
                staged_segment_count[segments]=0u;
                staged_segment_last[segments]=0u;
                staged_segment_finish[segments]=1u;
                ++segments;
                pair_cursor=ray_next_pair(pair);
                continue;
            }
            local_next=first;local_last=last;
            local_active=1u;column_pass_dirty=1u;
        }
        uint8_t remaining=(uint8_t)(local_last-local_next);
        uint8_t count=(remaining<budget)?remaining:budget;
        staged_segment_pair[segments]=pair;
        staged_segment_first[segments]=local_next;
        staged_segment_count[segments]=count;
        staged_segment_last[segments]=local_last;
        staged_segment_finish[segments]=(count==remaining);
        if(count)stage_pair_words(pair,local_next,count,staged_words+total);
        total=(uint8_t)(total+count);
        budget=(uint8_t)(budget-count);
        ++segments;
        if(count!=remaining)break;
        local_active=0u;
        pair_cursor=ray_next_pair(pair);
    }
    if(segments) {
        staged_segments=segments;
        staged_total_words=total;
        staged_ready=1u;
    }
}

static void render_columns(void) {
    if(!staged_ready)return;
    uint8_t offset=0u;
    for(uint8_t seg=0u; seg<staged_segments; ++seg) {
        uint8_t pair=staged_segment_pair[seg];
        uint8_t first=staged_segment_first[seg];
        uint8_t count=staged_segment_count[seg];
        uint8_t done=0u;
        while(done<count) {
            uint8_t y=(uint8_t)(first+done);
            uint8_t n=(uint8_t)(count-done);
            /* Page 2 starts at physical BAT row 63 (logical y=64) and wraps
             * to row 0 at logical y=65, so never stride across that wrap. */
            uint8_t physical_row=(uint8_t)((y&64u)?((y-1u)&63u):(y&63u));
            uint8_t until_page=(uint8_t)(64u-physical_row);
            if(n>8u)n=8u;
            if(n>until_page)n=until_page;
            pce_cpu_irq_disable();
#if RAY_PRESENT_CONTIGUOUS
            /* This branch is only safe for a physically contiguous BAT
             * column. Page 2's circular row shift wraps at y=65; y=64
             * switches the BAT half. The VDC word-address increment remains
             * 128 even while a raster interrupt changes scroll registers. */
            uint8_t readdress=(uint8_t)(done==0u || y==64u || y==65u);
#else
            uint8_t readdress=1u;
#endif
            if(readdress) {
#if RAY_INLINE_VDC_ADDRESS
                __asm__ volatile("st0 #0" ::: "memory");
                *IO_VDC_DATA=RAY_BAT_ADDRESS(y,pair);
#else
                pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,RAY_BAT_ADDRESS(y,pair));
#endif
            }
#if RAY_INLINE_VDC_ADDRESS
            __asm__ volatile("st0 #2" ::: "memory");
#else
            *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
#endif
            pce_memop((void*)IO_VDC_DATA,staged_words+offset+done,(uint16_t)(n<<1),PCE_MEMOP_INCR_ALT);
            pce_cpu_irq_enable();
            done=(uint8_t)(done+n);
        }
        offset=(uint8_t)(offset+count);
        upload_next_y=(uint8_t)(first+count);
        upload_last_y=staged_segment_last[seg];
        if(staged_segment_finish[seg]) {
            upload_active=0u;
            finish_column(pair);
        } else {
            upload_active=1u;
        }
    }
    ray_bat_words=(uint16_t)(ray_bat_words+staged_total_words);
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
    bat_bitmap_setup(ray_sheet_palette);
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
    next_column=RAY_FIRST_PAIR;cast_valid=0;upload_active=0;ray_bat_words=0;
    column_pairs_per_update=RAY_COLUMNS_PER_UPDATE;
#if RAY_WALL_CODEGEN
    ray_codegen_words=0;
#endif
    for(uint8_t c=0;c<128;++c)old_height[c]=0;
#endif
    draw_row=0;ray_redraws=0;
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
