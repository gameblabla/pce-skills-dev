#include <pce.h>
volatile uint8_t ticks;
__attribute__((interrupt)) void irq_timer(void) {
    *IO_IRQ_ACK=0;
    ++ticks;
}
int main(void) {
    pce_timer_set(6);
    pce_irq_enable(IRQ_TIMER);
    pce_timer_enable();
    pce_cpu_irq_enable();
    while (ticks<100) {}
    pce_timer_disable();
    for (;;) {}
}
