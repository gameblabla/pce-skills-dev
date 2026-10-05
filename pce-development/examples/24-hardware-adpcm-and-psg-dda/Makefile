# Standalone LLVM-MOS PCE CD SDK project.
.DEFAULT_GOAL := all

LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk

PROJECT := $(notdir $(CURDIR))
OUT := build/$(PROJECT).elf
SOURCES := $(wildcard src/*.c) $(wildcard src/*.S)
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0

.PHONY: all clean bios-check
all: $(OUT)

$(OUT): $(SOURCES) $(wildcard src/*.h) $(wildcard assets/*) | toolchain
	@mkdir -p $(dir $@)
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Isrc -Iassets $(SOURCES) -o $@ -Wl,-Map,$@.map

bios-check:
	@tools/check-pce-bios.sh

clean:
	@rm -rf build

.PHONY: encode-audio
encode-audio:
	python3 ../../tools/pce/softadpcm.py assets/chirp.wav build/chirp.softadpcm --rate 6991
