.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
PROJECT := $(notdir $(CURDIR))
OUT := build/$(PROJECT).pce
GEN := build/generated
.PHONY: all assets-check lint run debug clean
all: $(OUT)
assets-check:
	python3 tools/assetpack.py assets/level.json --check
$(GEN)/level_art.c $(GEN)/level_art.h &: assets/level.json tools/assetpack.py
	@mkdir -p $(GEN)
	python3 tools/assetpack.py assets/level.json --out $(GEN)
$(OUT): src/main.c $(GEN)/level_art.c $(GEN)/level_art.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -I$(GEN) src/main.c $(GEN)/level_art.c -o $@ -Wl,-Map,$@.map
run debug: $(OUT)
	@PCE_RUN_FRAMES="$(or $(PCE_RUN_FRAMES),120)" \
	 PCE_RUN_SCREENSHOT="$(PCE_RUN_SCREENSHOT)" \
	 PCE_HEADLESS_BASE_DIR="$(PCE_HEADLESS_BASE_DIR)" \
	 PCE_HEADLESS="$(PCE_HEADLESS)" \
	 tools/run-pce-headless.sh "$@" "$(OUT)"
clean:
	rm -rf build
