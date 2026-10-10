# Standalone LLVM-MOS PCE CD SDK project.
.DEFAULT_GOAL := all

LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk

PROJECT := $(notdir $(CURDIR))
OUT := build/$(PROJECT).pce
SOURCES := $(wildcard src/*.c) $(wildcard src/*.S)
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0

.PHONY: all clean
all: model-check $(OUT)

$(OUT): $(SOURCES) $(wildcard src/*.h) $(wildcard tools/*.h) $(filter-out assets/screenshot.png,$(wildcard assets/*)) | toolchain
	@mkdir -p $(dir $@)
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Isrc -Iassets $(SOURCES) -o $@ -Wl,--defsym=__rom_bank0=0x8000,--defsym=__rom_bank0_size=0x8000 -Wl,-Map,$@.map


clean:
	@rm -rf build

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

# Compact 16-bit Q4 P4TR. The trace is two 32-byte records, with no P2TR ABI.
.PHONY: trace trace-replay
trace: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/p4_trace.py --rom $(OUT) \
	 --elf $(OUT).elf --scenario tools/platformer-scenario.example.json \
	 --samples-out build/p4-trace-samples.json --output build/p4-trace-report.json
trace-replay:
	python3 tools/p4_trace.py --samples build/p4-trace-samples.json \
	 --output build/p4-trace-replay.json

# Transcript-derived local-model guardrails. Build the game only after checking
# API spellings and target scope; generated C is still compiled with -Werror.
.PHONY: model-check diagnose acceptance-check
model-check:
	python3 tools/model_guard.py scan .
diagnose:
	@if [ -z "$(LOG)" ]; then echo 'Usage: make diagnose LOG=build/compile.log' >&2; exit 2; fi
	python3 tools/model_guard.py diagnose "$(LOG)"
acceptance-check:
	python3 tools/model_guard.py evidence tools/evidence.json
