#include <stdint.h>
volatile int32_t player_x_q8, camera_x_q8;
int main(void) {
    player_x_q8=32L<<8;
    for(;;){
        camera_x_q8=player_x_q8-(112L<<8);
        if(camera_x_q8<0)camera_x_q8=0;
        if(camera_x_q8>(512L-256L)*256L)camera_x_q8=(512L-256L)*256L;
        player_x_q8+=256;
        if(player_x_q8>=512L*256L)player_x_q8=0;
    }
}
