#include <stdint.h>
volatile int16_t lane_x;
/* Ring position intentionally wraps at 256 world pixels (Q8). */
volatile uint16_t forward_y_q8;
int main(void) {
    lane_x=128;forward_y_q8=0;
    for(;;){
        ++lane_x;
        if(lane_x>208) lane_x=48;
        forward_y_q8+=768;
    }
}
