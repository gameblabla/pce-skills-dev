# Standalone LLVM-MOS PCE CD SDK project.
.DEFAULT_GOAL := all

LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk

PROJECT := $(notdir $(CURDIR))
OUT := build/$(PROJECT).pce
SOURCES := $(wildcard src/*.c) $(wildcard src/*.S)
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0

.PHONY: all clean
all: $(OUT)

$(OUT): $(SOURCES) $(wildcard src/*.h) $(wildcard tools/*.h) $(filter-out assets/screenshot.png,$(wildcard assets/*)) | toolchain
	@mkdir -p $(dir $@)
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Isrc -Iassets $(SOURCES) -o $@ -Wl,--defsym=__rom_bank0=0x8000,--defsym=__rom_bank0_size=0x8000 -Wl,-Map,$@.map


clean:
	@rm -rf build

.PHONY: convert-assets
convert-assets:
	python3 ../../tools/pce/picture.py assets/source.png --canvas 320x224 --out build/static-picture

# Headless run/debug: pass PCE_RUN_IMAGE for a packaged CD image.
PCE_RUN_IMAGE ?= $(if $(filter 1,$(PCE_CDROM2)),,$(OUT))
PCE_RUN_FRAMES ?= 120

.PHONY: run debug
run debug: $(PCE_RUN_IMAGE)
	@if [ -z "$(PCE_RUN_IMAGE)" ]; then \
	  echo 'For CD, set PCE_RUN_IMAGE to the packaged disc image; the application .bin is not bootable by itself.' >&2; \
	  exit 2; \
	fi
	@PCE_RUN_FRAMES="$(PCE_RUN_FRAMES)" \
	 PCE_RUN_SCREENSHOT="$(PCE_RUN_SCREENSHOT)" \
	 PCE_HEADLESS_BASE_DIR="$(PCE_HEADLESS_BASE_DIR)" \
	 PCE_HEADLESS="$(PCE_HEADLESS)" \
	 PCE_SYSTEM_CARD_BIOS="$(PCE_SYSTEM_CARD_BIOS)" \
	 PCE_COVERAGE="$(PCE_COVERAGE)" \
	 PCE_DEBUG_DISASM="$(PCE_DEBUG_DISASM)" \
	 tools/run-pce-headless.sh "$@" "$(PCE_RUN_IMAGE)"

# P2TR scenarios apply deterministic input and produce a text physics report.
PCE_PLATFORM_TRACE_ADDRESS ?=
PCE_PLATFORM_TRACE_ELF ?= $(OUT).elf
PCE_PLATFORM_TRACE_SYMBOL ?= pce_platformer_trace
PCE_PLATFORM_TRACE_SCENARIO ?= tools/platformer-scenario.example.json
PCE_PLATFORM_TRACE_OUTPUT ?= build/platformer-trace.json
PCE_PLATFORM_TRACE_BASE_DIR ?= build/platformer-trace-base
PCE_PLATFORM_TRACE_INITIAL_FRAMES ?= 2

.PHONY: trace
trace: $(PCE_RUN_IMAGE)
	@if [ -z "$(PCE_RUN_IMAGE)" ]; then \
	  echo 'For CD, set PCE_RUN_IMAGE to the packaged disc image.' >&2; exit 2; \
	fi
	PCE_HEADLESS="$(PCE_HEADLESS)" PCE_SYSTEM_CARD_BIOS="$(PCE_SYSTEM_CARD_BIOS)" \
	 python3 tools/platformer-trace.py --rom "$(PCE_RUN_IMAGE)" \
	 $(if $(PCE_PLATFORM_TRACE_ADDRESS),--address "$(PCE_PLATFORM_TRACE_ADDRESS)",--elf "$(PCE_PLATFORM_TRACE_ELF)" --symbol "$(PCE_PLATFORM_TRACE_SYMBOL)") \
	 --scenario "$(PCE_PLATFORM_TRACE_SCENARIO)" \
	 --base-dir "$(PCE_PLATFORM_TRACE_BASE_DIR)" \
 --initial-frames "$(PCE_PLATFORM_TRACE_INITIAL_FRAMES)" \
	 --output "$(PCE_PLATFORM_TRACE_OUTPUT)"
