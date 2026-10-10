#include <stdint.h>
volatile int16_t lane_x;
volatile uint32_t forward_y_q8;
int main(void) {
    lane_x=128;forward_y_q8=0;
    for(;;){
        ++lane_x;
        if(lane_x>208)lane_x=48;
        forward_y_q8+=768;
    }
}
