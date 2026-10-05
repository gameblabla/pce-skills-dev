#pragma once
#include <stdint.h>
typedef struct { int16_t x, top, width, collision_height, art_height; } DemoPlatform;
#define PCE_DEMO_SURFACE_COUNT 4
#define PCE_DEMO_WORLD_WIDTH 512
#define PCE_DEMO_FLOOR_TOP 176
static const DemoPlatform pce_demo_surfaces[PCE_DEMO_SURFACE_COUNT] = {
    {0,176,512,80,80},
    {104,144,48,8,16},
    {208,120,48,8,16},
    {352,144,48,8,16},
};
