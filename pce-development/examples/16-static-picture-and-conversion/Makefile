# Standalone LLVM-MOS PCE CD SDK project.
.DEFAULT_GOAL := all

LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk

PROJECT := $(notdir $(CURDIR))
OUT := build/$(PROJECT).pce
SOURCES := $(wildcard src/*.c) $(wildcard src/*.S)
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0

.PHONY: all clean bios-check
all: $(OUT)

$(OUT): $(SOURCES) $(wildcard src/*.h) $(filter-out assets/screenshot.png,$(wildcard assets/*)) | toolchain
	@mkdir -p $(dir $@)
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Isrc -Iassets $(SOURCES) -o $@ -Wl,--defsym=__rom_bank0=0x8000,--defsym=__rom_bank0_size=0x8000 -Wl,-Map,$@.map

bios-check:
	@tools/check-pce-bios.sh

clean:
	@rm -rf build

.PHONY: convert-assets
convert-assets:
	python3 ../../tools/pce/picture.py assets/source.png --canvas 320x224 --out build/static-picture
