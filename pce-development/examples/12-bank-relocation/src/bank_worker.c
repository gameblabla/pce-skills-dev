#include <stdint.h>

volatile uint8_t banked_result;

/* PCE_RAM_BANK_AT(1, 3) in main.c declares and maps this linker section. */
__attribute__((noinline, section("text.pce_ram_bank1")))
void banked_transform(void) {
    banked_result = 0x6a;
}
