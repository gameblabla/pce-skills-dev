#include <stdint.h>

volatile uint8_t banked_result;

/* PCE_ROM_BANK_AT(4, 3) in main.c declares and maps this linker section. */
__attribute__((noinline, section(".rom_bank4")))
void banked_transform(void) {
    banked_result = 0x6a;
}
