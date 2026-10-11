/* Experimental 128x128 VBlank BAT page switching, compressed two-color tiles.
 * This has only 32 raster scroll events/frame and changes the visible BXR
 * solely at VBlank. Each BAT tile stores 2x4 logical pixels (8 values),
 * quantized to the closest of a curated pair of PCE palette colors. It does
 * NOT preserve the 16-color appearance of the normal 128x128 example.
 */
#define main unused_original_main
#include "main.c"
#undef main
#include "pageflip_tiled_quant.h"
#ifndef RAY_TILE_FAST_QUANT
#define RAY_TILE_FAST_QUANT 1
#endif

volatile uint8_t ray_flip_front,ray_flip_pending;
static uint8_t flip_next_group,flip_pose_valid,flip_pose_angle;
static int16_t flip_pose_x,flip_pose_y;
#ifndef RAY_TILE_GROUPS_PER_UPDATE
#define RAY_TILE_GROUPS_PER_UPDATE 4u
#endif
#if RAY_TILE_GROUPS_PER_UPDATE != 2u && RAY_TILE_GROUPS_PER_UPDATE != 4u && RAY_TILE_GROUPS_PER_UPDATE != 8u
#error "groups per update must be 2, 4 or 8"
#endif
static uint16_t flip_pixel_rows[64],flip_stage[RAY_TILE_GROUPS_PER_UPDATE][32];

static void flip_setup(void) {
    pce_cpu_irq_disable();
    pce_vdc_bg_disable();
    pce_vdc_set_resolution(512,224,VCE_PIXEL_CLOCK_10MHZ);
    pce_vdc_bg_set_size(VDC_BG_SIZE_128_64);
    pce_vdc_set_copy_word();
    pce_vce_set_color(0,ray_sheet_palette[0]);
    for(uint8_t g=0;g<16u;++g) {
        pce_vce_set_color((uint16_t)g*16u+1u,ray_sheet_palette[ray_tiled_palettes[g][0]]);
        pce_vce_set_color((uint16_t)g*16u+2u,ray_sheet_palette[ray_tiled_palettes[g][1]]);
    }
    /* A fixed 256-pattern atlas: 2 logical pixels per row x 4 rows.
     * The PCE expands each pixel to 4x2 physical pixels. Each atlas bit
     * selects palette entry 1 or 2 (never translucent color index 0). */
    for(uint16_t glyph=0;glyph<256u;++glyph) {
        pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,(uint16_t)(0x2000u+glyph*16u));
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
        for(uint8_t y=0;y<8u;++y) {
            uint8_t v=(uint8_t)((glyph>>(6u-2u*(y>>1)))&3u);
            uint8_t hi=(v&2u)?0xf0u:0u,lo=(v&1u)?0x0fu:0u;
            uint8_t p1=(uint8_t)(hi|lo),p0=(uint8_t)(p1^0xffu);
            *IO_VDC_DATA=(uint16_t)(p0|((uint16_t)p1<<8));
        }
        for(uint8_t y=0;y<8u;++y)*IO_VDC_DATA=0u;
    }
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,0u);
    *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
    for(uint16_t i=0;i<8192u;++i)*IO_VDC_DATA=0x0200u;
    ray_flip_front=0u;ray_flip_pending=0u;flip_next_group=0u;flip_pose_valid=0u;
    bat_bitmap_display();
    pce_cpu_irq_disable();
    pce_vdc_poke(VDC_REG_CONTROL,VDC_CONTROL_ENABLE_BG|
                 VDC_CONTROL_IRQ_SCANLINE|VDC_CONTROL_IRQ_VBLANK|
                 VDC_CONTROL_VRAM_ADD_128);
    pce_cpu_irq_enable();
}

static void flip_render_group(uint8_t group,uint16_t *dest) {
    for(uint8_t half=0u;half<2u;++half) {
        stage_pair_words(group,(uint8_t)(half<<6),64u,flip_pixel_rows);
        for(uint8_t tile=0u;tile<16u;++tile) {
#if RAY_TILE_FAST_QUANT
            /* Four packed source-pixel pairs make the 2x4 tile. A ROM
             * lookup combines each pair's error and two glyph-mask bits,
             * avoiding 16 individual palette/texture lookups per tile. */
            uint8_t p0=(uint8_t)flip_pixel_rows[(uint8_t)(tile<<2)];
            uint8_t p1=(uint8_t)flip_pixel_rows[(uint8_t)((tile<<2)+1u)];
            uint8_t p2=(uint8_t)flip_pixel_rows[(uint8_t)((tile<<2)+2u)];
            uint8_t p3=(uint8_t)flip_pixel_rows[(uint8_t)((tile<<2)+3u)];
            uint8_t g0=ray_tiled_best_pair[p0];
            uint8_t g1=ray_tiled_best_pair[p3];
            const uint8_t *e0=ray_tiled_pair_error[g0];
            const uint8_t *e1=ray_tiled_pair_error[g1];
            uint8_t score0=(uint8_t)(e0[p0]+e0[p1]+e0[p2]+e0[p3]);
            uint8_t score1=(uint8_t)(e1[p0]+e1[p1]+e1[p2]+e1[p3]);
            uint8_t pal=(score1<score0)?g1:g0;
            const uint8_t *mask=ray_tiled_pair_mask[pal];
            uint8_t pattern=(uint8_t)((mask[p0]<<6)|(mask[p1]<<4)|
                                      (mask[p2]<<2)|mask[p3]);
#else
            uint8_t c[8];
            for(uint8_t row=0u;row<4u;++row) {
                uint8_t v=(uint8_t)flip_pixel_rows[(uint8_t)((tile<<2)+row)];
                c[row<<1]=v>>4;c[(row<<1)+1u]=v&15u;
            }
            uint8_t g0=ray_tiled_best_pair[(uint8_t)((c[0]<<4)|c[1])];
            uint8_t g1=ray_tiled_best_pair[(uint8_t)((c[6]<<4)|c[7])];
            uint8_t score0=0,score1=0;
            for(uint8_t k=0u;k<8u;++k) {
                score0=(uint8_t)(score0+ray_tiled_error[g0][c[k]]);
                score1=(uint8_t)(score1+ray_tiled_error[g1][c[k]]);
            }
            uint8_t pal=(score1<score0)?g1:g0;
            const uint8_t *q=ray_tiled_quant[pal];
            uint8_t pattern=0u;
            for(uint8_t k=0u;k<8u;++k)
                pattern=(uint8_t)((pattern<<1)|q[c[k]]);
#endif
            dest[(uint8_t)((half<<4)+tile)]=(uint16_t)(((uint16_t)pal<<12)|0x0200u|pattern);
        }
    }
}

static void flip_transfer(uint8_t group,uint8_t page,const uint16_t *data) {
    const uint16_t base=(uint16_t)((uint16_t)page*64u+group);
    pce_cpu_irq_disable();
    pce_vdc_poke(VDC_REG_VRAM_WRITE_ADDR,base);
    *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
    pce_cpu_irq_enable();
    for(uint8_t i=0u;i<32u;i+=8u) {
        pce_cpu_irq_disable();
        *IO_VDC_INDEX=VDC_REG_VRAM_DATA;
        pce_memop((void*)IO_VDC_DATA,data+i,16u,PCE_MEMOP_INCR_ALT);
        pce_cpu_irq_enable();
    }
    ray_bat_words=(uint16_t)(ray_bat_words+32u);
}

int main(void) {
    flip_setup();
    world_x=3*256+128;world_y=3*256+128;angle=0;
    ray_redraws=0;ray_bat_words=0;
    uint16_t frame=0;
    for(;;) {
        uint8_t buttons=(uint8_t)~pce_joypad_read();
        if((frame&5u)==0u) {
            if(buttons&KEY_LEFT)angle=(uint8_t)((angle+15u)&15u);
            if(buttons&KEY_RIGHT)angle=(uint8_t)((angle+1u)&15u);
        }
        int16_t old_x=world_x,old_y=world_y;
        wall_blocked=0u;
        if(buttons&(KEY_UP|KEY_DOWN)) {
            int16_t x=world_x,y=world_y;
            if(buttons&KEY_UP){x+=player_step_x[angle];y+=player_step_y[angle];}
            else {x-=player_step_x[angle];y-=player_step_y[angle];}
            if(material_at(x,world_y))wall_blocked=1;else world_x=x;
            if(material_at(world_x,y))wall_blocked=1;else world_y=y;
        }
        if(flip_next_group==0u) {
            if(flip_pose_valid && world_x==flip_pose_x && world_y==flip_pose_y && angle==flip_pose_angle) {
                uint8_t before=bat_frames;while(before==bat_frames) {}
                publish(frame,buttons,world_x-old_x,world_y-old_y);++frame;
                continue;
            }
            flip_pose_valid=1u;flip_pose_x=world_x;flip_pose_y=world_y;flip_pose_angle=angle;
            render_world_x=world_x;render_world_y=world_y;
            cast_scene();
        }
        for(uint8_t group=0u;group<RAY_TILE_GROUPS_PER_UPDATE;++group)
            flip_render_group((uint8_t)(flip_next_group+group),flip_stage[group]);
        uint8_t before=bat_frames;while(before==bat_frames) {}
        const uint8_t back=(uint8_t)(ray_flip_front^1u);
        for(uint8_t group=0u;group<RAY_TILE_GROUPS_PER_UPDATE;++group)
            flip_transfer((uint8_t)(flip_next_group+group),back,flip_stage[group]);
        flip_next_group=(uint8_t)(flip_next_group+RAY_TILE_GROUPS_PER_UPDATE);
        if(flip_next_group==64u) {
            flip_next_group=0u;ray_flip_pending=1u;
            while(ray_flip_pending) {}
        }
        publish(frame,buttons,world_x-old_x,world_y-old_y);++frame;
    }
}
