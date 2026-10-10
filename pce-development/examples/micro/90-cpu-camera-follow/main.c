#include <stdint.h>
/* Q4 fits an entire 512-pixel world into signed 16 bits. */
volatile int16_t player_x_q4, camera_x_q4;
int main(void) {
    player_x_q4=32<<4;
    for (;;) {
        camera_x_q4=player_x_q4-(112<<4);
        if (camera_x_q4<0) camera_x_q4=0;
        if (camera_x_q4>(256<<4)) camera_x_q4=256<<4;
        player_x_q4+=16;
        if (player_x_q4>=512<<4) player_x_q4=0;
    }
}
