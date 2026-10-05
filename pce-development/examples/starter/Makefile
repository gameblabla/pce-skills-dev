# Copy this Makefile and the files in tools/ into a new project.
# Add project-specific build rules after verifying its LLVM-MOS SDK inputs.
.DEFAULT_GOAL := all

LLVM_MOS_CC ?= mos-pce-clang

include tools/llvm-mos-sdk.mk

.PHONY: all clean
all: toolchain

.PHONY: run debug
PCE_RUN_IMAGE ?= $(if $(filter 1,$(PCE_CDROM2)),,$(OUT))
PCE_RUN_FRAMES ?= 120

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

clean:
	@rm -rf build
