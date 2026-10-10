/* racing G2TR-only instrumentation probe: intentionally no graphics.
 * Replace this toy state update with real game facts in your own racing.
 * A trace without independent screenshot/interaction evidence proves NO visuals.
 */
#include <pce.h>
#include "genre_trace.h"
volatile G2Trace pce_genre_trace[2];
static volatile uint8_t ticks;
__attribute__((interrupt)) void irq_vdc(void) {
    uint8_t s=*IO_VDC_STATUS;
    if(s & VDC_FLAG_VBLANK) ++ticks;
}
static void publish(uint32_t frame) {
    volatile G2Trace *t=&pce_genre_trace[frame&1];
    uint16_t n=(uint16_t)(frame<<1);
    t->sequence=n|1;
    t->magic[0]='G';t->magic[1]='2';t->magic[2]='T';t->magic[3]='R';
    t->version=2;t->genre=4;t->scene=1;t->flags=G2TR_FLAG_ACTIVE; /* no renderer in this probe */
    t->frame=frame;t->buttons=(uint16_t)~pce_joypad_read();
    t->x_q8=G2TR_Q8(120);t->y_q8=G2TR_Q8(0);
    t->vx_q8=0;t->vy_q8=G2TR_Q8(2);t->camera_x_q8=t->camera_y_q8=0;
    t->screen_x_q8=t->x_q8;t->screen_y_q8=t->y_q8;
    t->state[0]=G2TR_Q8(0); /* lateral lane offset */
    t->state[1]=G2TR_Q8(frame*2); /* forward distance */
    t->state[2]=G2TR_Q8(2); /* speed */ t->state[3]=3; /* visible traffic */
    t->sequence=n;
}
int main(void) {
    pce_vdc_irq_vblank_enable();pce_irq_enable(IRQ_VDC);pce_cpu_irq_enable();
    uint32_t frame=0;
    for(;;) {
        uint8_t before=ticks;while(before==ticks) {}
        publish(frame++);
    }
}
