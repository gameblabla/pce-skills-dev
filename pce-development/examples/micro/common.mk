# Shared build rules: each directory contains only main.c and Makefile.
.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include ../../starter/tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
OUT := build/$(notdir $(CURDIR)).pce
# In the toolkit LIBCOMMON lives at pce-development/libcommon. Exported
# micro projects vendor their own libcommon at <export>/libcommon.
ifneq ($(wildcard ../../libcommon/Makefile),)
LIBCOMMON_DIR := $(abspath ../../libcommon)
ARITH_GUARD := ../../workflows/arith_guard.py
else
LIBCOMMON_DIR := $(abspath ../../../libcommon)
ARITH_GUARD := ../../../workflows/arith_guard.py
endif
LIBCOMMON_A := $(LIBCOMMON_DIR)/build/libpcecommon.a
# Opt-in bitmap interrupt: not part of libcommon.a, because a strong IRQ
# symbol in a generic archive could be extracted by an unrelated program.
ifeq ($(NATIVE_BITMAP_IRQ),1)
PCE_FLAGS += -DBAT_BITMAP_NATIVE_IRQ
NATIVE_BITMAP_SRC := $(LIBCOMMON_DIR)/src/bat_bitmap_irq.S
endif
$(LIBCOMMON_A): $(wildcard $(LIBCOMMON_DIR)/src/*.c) $(wildcard $(LIBCOMMON_DIR)/src/*_lut.h) $(wildcard $(LIBCOMMON_DIR)/include/*.h)
	$(MAKE) --no-print-directory -C $(LIBCOMMON_DIR) all

.PHONY: all clean
all: $(OUT)
$(OUT): main.c $(wildcard ../*.h) $(wildcard $(LIBCOMMON_DIR)/include/*.h) $(NATIVE_BITMAP_SRC) $(LIBCOMMON_A) | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -I$(LIBCOMMON_DIR)/include $< $(NATIVE_BITMAP_SRC) $(LIBCOMMON_A) -o $@ -Wl,-Map,$@.map
clean:
	@rm -rf build

# Runs always go through the common project wrapper; zero UI setup in audio.
PCE_RUN_FRAMES ?= 120
.PHONY: run debug
run debug: $(OUT)
	@PCE_RUN_FRAMES="$(PCE_RUN_FRAMES)" \
	 PCE_RUN_SCREENSHOT="$(PCE_RUN_SCREENSHOT)" \
	 PCE_HEADLESS_BASE_DIR="$(PCE_HEADLESS_BASE_DIR)" \
	 PCE_HEADLESS="$(PCE_HEADLESS)" \
	 PCE_COVERAGE="$(PCE_COVERAGE)" \
	 ../../starter/tools/run-pce-headless.sh "$@" "$(OUT)"

.PHONY: arith-elf
arith-elf: $(OUT)
	python3 $(ARITH_GUARD) elf $(OUT).elf
