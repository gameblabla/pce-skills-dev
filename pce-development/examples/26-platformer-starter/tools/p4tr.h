#ifndef P4TR_H
#define P4TR_H
#include <stdint.h>
/* P4TR v4, 32 bytes; all values <=16 bits. No 32-bit ABI baggage.
 * Two records are atomically published via odd/even byte sequence. */
typedef struct __attribute__((packed)) {
    uint8_t magic[4];
    uint8_t version,scene,flags,events,sequence,buttons;
    uint16_t frame;
    int16_t x_q4,y_q4,vx_q4,vy_q4,camera_q4;
    int16_t draw_x,draw_y;
    uint16_t race_lane,race_progress;
    uint8_t surface_count,live_sprites;
} P4Trace;
_Static_assert(sizeof(P4Trace)==32,"P4TR must be exactly 32 bytes");
extern volatile P4Trace p4_trace[2];
/* Keep transition events visible for three gameplay ticks. This covers
 * emulator screenshots/memread skipping a tick during an IRQ or transfer. */
static uint8_t p4_event_bits,p4_event_ticks;
static void p4_events_reset(void) {p4_event_bits=0;p4_event_ticks=0;}
static uint8_t p4_event_latch(uint8_t new_events) {
    if(new_events){p4_event_bits=new_events;p4_event_ticks=3;}
    else if(p4_event_ticks) --p4_event_ticks;
    return p4_event_ticks?p4_event_bits:0;
}
static void p4_publish(uint16_t frame, uint8_t scene, uint8_t buttons,
                       uint8_t events, uint8_t blocked, const P4Motion *p,
                       uint16_t lane, uint16_t progress, uint8_t *active,
                       uint8_t *sequence) {
    uint8_t index=(uint8_t)(*active^1u);
    volatile P4Trace *t=&p4_trace[index];
    *sequence=(uint8_t)((*sequence+2u)&0xFEu);
    t->sequence=(uint8_t)(*sequence|1u);
    t->magic[0]='P';t->magic[1]='4';t->magic[2]='T';t->magic[3]='R';
    t->version=4;t->scene=scene;
    t->flags=(p->grounded?P4_GROUNDED:0)|(p->left?P4_FACING_LEFT:0)|
             (blocked?P4_BLOCKED_X:0);
    t->events=p4_event_latch(events);t->buttons=buttons;t->frame=frame;
    t->x_q4=p->x;t->y_q4=p->y;t->vx_q4=p->vx;t->vy_q4=p->vy;
    t->camera_q4=p->camera;
    t->draw_x=(int16_t)((p->x-p->camera)/16+P4_BOX_DX);
    t->draw_y=(int16_t)(p->y/16+P4_BOX_DY);
    t->race_lane=lane;t->race_progress=progress;
    t->surface_count=PCE_DEMO_SURFACE_COUNT;t->live_sprites=scene?2:1;
    t->sequence=*sequence;
    *active=index;
}
#endif
