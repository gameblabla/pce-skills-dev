# Shared build rules: each directory contains only main.c and Makefile.
.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include ../../starter/tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
OUT := build/$(notdir $(CURDIR)).pce
.PHONY: all clean
all: $(OUT)
$(OUT): main.c $(wildcard ../*.h) | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) $< -o $@ -Wl,-Map,$@.map
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
