#define PCE_CONFIG_IMPLEMENTATION
#include <pce.h>

PCE_ROM_BANK_AT(4,3);
extern volatile uint8_t banked_result;
void banked_transform(void);

int main(void) {
    uint8_t previous_bank = pce_bank3_get();
    pce_rom_bank4_map();
    banked_transform();
    pce_bank3_set(previous_bank); /* critical: restore MPR3 */
    for (;;) {} /* Inspect banked_result in the debugger (0x6a). */
}
