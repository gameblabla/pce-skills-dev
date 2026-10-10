#include <pce.h>
volatile uint8_t counter;
int main(void) {
    pce_cpu_irq_disable();
    ++counter;
    pce_cpu_irq_enable();
    for (;;) {}
}
