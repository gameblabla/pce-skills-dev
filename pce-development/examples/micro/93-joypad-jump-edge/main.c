#include <pce.h>
volatile uint8_t jumped,previous_jump;
int main(void) {
    previous_jump=0;
    for(;;){
        uint8_t now=(uint8_t)((~pce_joypad_read()&KEY_1)!=0);
        jumped=(uint8_t)(now && !previous_jump);
        previous_jump=now;
    }
}
