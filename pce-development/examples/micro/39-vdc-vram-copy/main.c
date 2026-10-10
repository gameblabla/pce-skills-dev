#include <pce.h>
static const uint8_t tile[32] = {
    0xff,0,0xff,0,0xff,0,0xff,0,
    0xff,0,0xff,0,0xff,0,0xff,0
};
int main(void) {
    pce_vdc_set_copy_word();
    pce_vdc_copy_to_vram(0x0800,tile,sizeof(tile));
    for (;;) {}
}
