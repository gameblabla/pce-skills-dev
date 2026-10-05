#include <pce.h>
#include "demo_video.h"
#include "demo_assets.h"

volatile uint8_t demo_vblank_count;
static volatile uint8_t parallax_enabled;
static volatile uint8_t parallax_band;
static uint16_t bat[64 * 32];

__attribute__((interrupt)) void irq_vdc(void) {
    uint8_t status = *IO_VDC_STATUS;
    if (status & VDC_FLAG_VBLANK) {
        ++demo_vblank_count;
        if (parallax_enabled) {
            parallax_band = 0;
            pce_vdc_poke(VDC_REG_SCANLINE, 64);
        }
    }
    if ((status & VDC_FLAG_SCANLINE) && parallax_enabled) {
        static const uint16_t band_scroll[] = {0, 12, 28, 48};
        if (parallax_band < 3) ++parallax_band;
        pce_vdc_poke(VDC_REG_BG_SCROLL_X, band_scroll[parallax_band]);
        if (parallax_band < 3)
            pce_vdc_poke(VDC_REG_SCANLINE, (uint16_t)(64u * (parallax_band + 1u)));
    }
}

void demo_video_init(uint16_t width_pixels, uint8_t vce_flags) {
    pce_vdc_bg_disable();
    pce_vdc_sprite_disable();
    pce_vdc_set_resolution(width_pixels, 224, vce_flags);
    pce_vdc_bg_set_size(VDC_BG_SIZE_64_32);
    pce_vdc_set_copy_word();
    pce_vce_copy_palette(0, pce_demo_palette, 1);
    pce_vce_copy_palette(16, pce_demo_palette, 1);
    pce_vce_copy_palette(17, pce_demo_palette, 1);
    pce_vce_copy_palette(18, pce_demo_palette, 1);
    pce_vdc_copy_to_vram(0x0800, pce_demo_patterns, sizeof(pce_demo_patterns));
    for (uint16_t y = 0; y < 32; ++y) {
        for (uint16_t x = 0; x < 64; ++x) {
            uint16_t tile = (uint16_t)(0x80u + ((x / 4u + y / 4u) & 3u));
            bat[y * 64u + x] = tile;
        }
    }
    pce_vdc_copy_to_vram(0x0000, bat, sizeof(bat));
    pce_vdc_irq_vblank_enable();
    pce_irq_enable(IRQ_VDC);
    pce_vdc_bg_enable();
    pce_cpu_irq_enable();
}

void demo_wait_frame(void) {
    uint8_t previous = demo_vblank_count;
    while (previous == demo_vblank_count) { }
}

void demo_set_scroll(uint16_t x, uint16_t y) {
    pce_vdc_poke(VDC_REG_BG_SCROLL_X, x);
    pce_vdc_poke(VDC_REG_BG_SCROLL_Y, y);
}

void demo_set_color(uint8_t palette, uint8_t color, uint16_t value) {
    pce_vce_set_color(VCE_COLOR_INDEX(palette, color), value);
}

void demo_upload_sprite_patterns(void) {
    pce_vdc_copy_to_vram(0x1000, pce_demo_sprite_pattern, sizeof(pce_demo_sprite_pattern));
    pce_vdc_sprite_set_table_start(0x7f00);
    pce_vdc_sprite_enable();
}

void demo_draw_sprite(int16_t x, int16_t y, uint16_t pattern_word, uint16_t attr) {
    demo_draw_sprite_slot(0, x, y, pattern_word, attr);
}

void demo_draw_sprite_slot(uint8_t slot, int16_t x, int16_t y,
                           uint16_t pattern_word, uint16_t attr) {
    vdc_sprite_t sprite;
    if (slot >= 64) return;
    sprite.y = (uint16_t)(y + 64);
    sprite.x = (uint16_t)(x + 32);
    sprite.pattern = pattern_word;
    sprite.attr = attr;
    pce_vdc_copy_to_vram((uint16_t)(0x7f00u + (uint16_t)slot * 4u),
                         &sprite, sizeof(sprite));
}

void demo_hide_sprite_slot(uint8_t slot) {
    const vdc_sprite_t hidden = {0, 0, 0, 0};
    if (slot < 64)
        pce_vdc_copy_to_vram((uint16_t)(0x7f00u + (uint16_t)slot * 4u),
                             &hidden, sizeof(hidden));
}

void demo_draw_bitmap_text_pce(void) {
    static const uint8_t glyphs[3][8] = {
        {0xf8,0x84,0x84,0xf8,0x80,0x80,0x80,0x00},
        {0x78,0x84,0x80,0x80,0x80,0x84,0x78,0x00},
        {0xf8,0x80,0x80,0xf0,0x80,0x80,0xf8,0x00}
    };
    uint8_t patterns[96] = {0};
    uint16_t bat_words[3] = {132, 133, 134};
    for (uint8_t glyph = 0; glyph < 3; ++glyph)
        for (uint8_t row = 0; row < 8; ++row)
            patterns[(uint16_t)glyph * 32u + (uint16_t)row * 2u] = glyphs[glyph][row];
    pce_vdc_copy_to_vram(0x0840, patterns, sizeof(patterns));
    pce_vdc_copy_to_vram(0x0000, bat_words, sizeof(bat_words));
}

void demo_enable_parallax_bands(void) {
    parallax_band = 0;
    parallax_enabled = 1;
    pce_vdc_irq_scanline_enable();
    pce_vdc_poke(VDC_REG_SCANLINE, 64);
}
