#include <pce.h>
int main(void) {
    static const uint8_t zeros[32] = {0};
    pce_vdc_set_copy_word();
    pce_vdc_copy_to_vram(0x0800,zeros,sizeof(zeros));
    for (;;) {}
}
