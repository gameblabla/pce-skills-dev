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

/* Sprite patterns at VRAM word 0x6000; SAT uses 32-word address units. */
#define DEMO_PLAYER_PATTERN 0x0300
#define DEMO_SHOT_PATTERN 0x0302
#define DEMO_ENEMY_PATTERN 0x0304
#define DEMO_HUD_PATTERN 0x0306
#define DEMO_POSE_PATTERN 0x0308
uint16_t demo_map_tile(uint16_t world_column, uint8_t row);
uint8_t demo_read_pad(void);
