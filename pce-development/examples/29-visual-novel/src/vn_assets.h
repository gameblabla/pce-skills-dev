#ifndef VN_ASSETS_H
#define VN_ASSETS_H
#define VN_BG_WORD 0x0800u
#define VN_BG_PALETTES 1
#define VN_SPRITE_WORD 0x6000u
#define VN_SAT_WORD 0x7f00u
#define VN_MOUTH_X 98
#define VN_MOUTH_Y 120
extern const unsigned char vn_patterns[9536];
extern const unsigned char vn_bat[1792];
extern const unsigned char vn_bg_palette[32];
extern const unsigned char vn_sprite_palette[32];
extern const unsigned char vn_mouth_patterns[256];
#endif
