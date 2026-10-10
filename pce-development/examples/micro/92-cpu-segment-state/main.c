#include <stdint.h>
volatile uint8_t scene;
volatile uint16_t distance;
int main(void) {
    scene=0;distance=0;
    for(;;){
        if(++distance>=440){
            scene^=1;
            distance=0;
        }
    }
}
