#include <pce.h>
/* Timer-based debugger markers; no visual indicator or graphics workload. */
volatile uint16_t debug_ticks;
volatile uint8_t debug_marker;

__attribute__((interrupt)) void irq_timer(void) {
    *IO_IRQ_ACK = 0;
    ++debug_ticks;
    debug_marker = (uint8_t)debug_ticks;
}

int main(void) {
    pce_timer_set(6);
    pce_irq_enable(IRQ_TIMER);
    pce_timer_enable();
    pce_cpu_irq_enable();
    for (;;) {}
}
