#include <pce.h>
volatile int16_t lane_x;
int main(void) {
    lane_x=128;
    for(;;){
        uint8_t keys=(uint8_t)~pce_joypad_read();
        if((keys&KEY_LEFT)&&lane_x>48)--lane_x;
        if((keys&KEY_RIGHT)&&lane_x<208)++lane_x;
    }
}
