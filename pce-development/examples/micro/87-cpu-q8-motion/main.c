#include <stdint.h>
volatile int32_t world_x_q8;
volatile int16_t velocity_q8;
int main(void) {
    world_x_q8=0;
    velocity_q8=96;
    for(;;)world_x_q8+=velocity_q8;
}
