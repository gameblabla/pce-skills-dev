# Standalone LLVM-MOS PCE CD SDK project.
.DEFAULT_GOAL := all

PCE_CDROM2 ?= 0
LLVM_MOS_CC ?= $(if $(filter 1,$(PCE_CDROM2)),mos-pce-cd-clang,mos-pce-clang)
include tools/llvm-mos-sdk.mk

PROJECT := $(notdir $(CURDIR))
ifeq ($(PCE_CDROM2),1)
OUT := build/$(PROJECT).bin
else
OUT := build/$(PROJECT).pce
endif
SOURCES := $(filter-out src/softadpcm_player_cdrom2.c,$(wildcard src/*.c)) $(wildcard src/*.S)
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
ifeq ($(PCE_CDROM2),1)
SOURCES += src/softadpcm_player_cdrom2.c
PCE_FLAGS += -DPCE_SOFTADPCM_CDROM2
else
PCE_FLAGS += -DPCE_SOFTADPCM_HUCARD_IRQ
endif

.PHONY: all clean bios-check
all: $(OUT)

$(OUT): $(SOURCES) $(wildcard src/*.h) $(filter-out assets/screenshot.png,$(wildcard assets/*)) | toolchain
	@mkdir -p $(dir $@)
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Isrc -Iassets $(SOURCES) -o $@ -Wl,--defsym=__rom_bank0=0x8000,--defsym=__rom_bank0_size=0x8000 -Wl,-Map,$@.map

bios-check:
	@tools/check-pce-bios.sh

clean:
	@rm -rf build

.PHONY: encode-audio
encode-audio:
	python3 ../../tools/pce/softadpcm.py assets/chirp.wav build/chirp.softadpcm --rate 6991
