#include <stdint.h>
volatile int16_t previous_feet, current_feet;
volatile uint8_t landed;
int main(void) {
    previous_feet=128;current_feet=128;
    for(;;){
        landed=(uint8_t)(previous_feet<=176 && current_feet>=176);
        previous_feet=current_feet;
        if(current_feet<192)current_feet+=2;
    }
}
