#ifndef PCE_PLATFORMER_Q4_H
#define PCE_PLATFORMER_Q4_H
/* Pure 16-bit, signed Q4 physics. 512x224 world fits with headroom.
 * The CPU never multiplies, divides, or loads a 32-bit integer here.
 * Keep this header byte-identical in both starter projects. */
#include <stdint.h>
#include "platform_layout.h"
/* All Q4 world positions must fit signed 16 bits. */
_Static_assert(PCE_DEMO_WORLD_WIDTH<=2047,"Q4 world width exceeds int16");
_Static_assert(PCE_DEMO_FLOOR_TOP<240,"Q4 floor should stay below drawable screen");
#define P4(x) ((int16_t)((x) * 16))
#define P4_WIDTH PCE_DEMO_WORLD_WIDTH
#define P4_PLAYER_W 16
#define P4_BOX_DX 3
#define P4_BOX_DY 1
#define P4_BOX_W 10
#define P4_BOX_H 15
#define P4_GRAVITY 4
#define P4_JUMP (-80)
#define P4_TERMINAL 96
#define P4_WALK 16
#define P4_GROUNDED 1u
#define P4_FACING_LEFT 2u
#define P4_BLOCKED_X 4u
#define P4_LANDED 1u
#define P4_JUMPED 2u

typedef struct {
    int16_t x, y, vx, vy, camera;
    uint8_t grounded, left, before_jump;
} P4Motion;

static void p4_reset(P4Motion *p) {
    p->x=P4(32);p->y=P4(PCE_DEMO_FLOOR_TOP-P4_PLAYER_W);
    p->vx=0;p->vy=0;p->camera=0;
    p->grounded=1;p->left=0;p->before_jump=0;
}
static uint8_t p4_overlaps(const P4Motion *p, const DemoPlatform *s) {
    return (uint8_t)(p->x+P4(P4_BOX_DX+P4_BOX_W)>P4(s->x) &&
                     p->x+P4(P4_BOX_DX)<P4(s->x+s->width));
}
static uint8_t p4_supported(const P4Motion *p) {
    uint8_t i;
    for(i=0;i<PCE_DEMO_SURFACE_COUNT;++i)
        if(p->y+P4(P4_BOX_DY+P4_BOX_H)==P4(pce_demo_surfaces[i].top) &&
           p4_overlaps(p,&pce_demo_surfaces[i]))return 1;
    return 0;
}
__attribute__((noinline)) static uint8_t p4_tick(P4Motion *p,uint8_t buttons,uint8_t *events) {
    int16_t old_feet=p->y+P4(P4_BOX_DY+P4_BOX_H);
    int16_t new_feet;
    uint8_t i, blocked=0, jump=(uint8_t)((buttons&KEY_1)!=0);
    *events=0;
    if((buttons&KEY_LEFT) && !(buttons&KEY_RIGHT)) {p->vx=-P4_WALK;p->left=1;}
    else if((buttons&KEY_RIGHT) && !(buttons&KEY_LEFT)) {p->vx=P4_WALK;p->left=0;}
    else p->vx=0;
    p->x+=p->vx;
    if(p->x<0){p->x=0;blocked=1;}
    if(p->x>P4(P4_WIDTH-P4_PLAYER_W)){p->x=P4(P4_WIDTH-P4_PLAYER_W);blocked=1;}
    if(p->grounded&&!p4_supported(p))p->grounded=0;
    if(jump&&!p->before_jump&&p->grounded){
        p->grounded=0;p->vy=P4_JUMP;*events|=P4_JUMPED;
    }
    p->before_jump=jump;
    if(!p->grounded){
        p->vy+=P4_GRAVITY;
        if(p->vy>P4_TERMINAL)p->vy=P4_TERMINAL;
        p->y+=p->vy;
    }else p->vy=0;
    new_feet=p->y+P4(P4_BOX_DY+P4_BOX_H);
    if(!p->grounded&&p->vy>=0){
        for(i=0;i<PCE_DEMO_SURFACE_COUNT;++i){
            int16_t top=P4(pce_demo_surfaces[i].top);
            if(old_feet<=top && new_feet>=top && p4_overlaps(p,&pce_demo_surfaces[i])){
                p->y=top-P4(P4_BOX_DY+P4_BOX_H);
                p->vy=0;p->grounded=1;*events|=P4_LANDED;
                break;
            }
        }
    }
    /* Constant 112px screen anchor; camera stays inside a 512px map. */
    p->camera=p->x>P4(104)?(int16_t)(p->x-P4(104)):0;
    if(p->camera>P4(P4_WIDTH-256))p->camera=P4(P4_WIDTH-256);
    return blocked;
}
#endif
