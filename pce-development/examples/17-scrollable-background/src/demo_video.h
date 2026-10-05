#pragma once
#include <stdint.h>

extern volatile uint8_t demo_vblank_count;
void demo_video_init(uint16_t width_pixels, uint8_t vce_flags);
void demo_wait_frame(void);
void demo_set_scroll(uint16_t x, uint16_t y);
void demo_set_color(uint8_t palette, uint8_t color, uint16_t value);
void demo_upload_sprite_patterns(void);
void demo_draw_sprite(int16_t x, int16_t y, uint16_t pattern_word, uint16_t attr);
void demo_draw_sprite_slot(uint8_t slot, int16_t x, int16_t y,
                           uint16_t pattern_word, uint16_t attr);
void demo_hide_sprite_slot(uint8_t slot);
void demo_draw_bitmap_text_pce(void);
void demo_enable_parallax_bands(void);
