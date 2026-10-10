#include <pce.h>
volatile uint8_t ticks;
__attribute__((interrupt)) void irq_timer(void) {
    *IO_IRQ_ACK = 0;
    ++ticks;
}
int main(void) {
    pce_timer_set(6); /* approximately 1 kHz */
    pce_irq_enable(IRQ_TIMER);
    pce_timer_enable();
    pce_cpu_irq_enable();
    for (;;) {}
}
