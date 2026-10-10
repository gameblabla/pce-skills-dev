.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
OUT := build/34-rendered-raycaster.pce
.PHONY: all run trace visual-test clean
all: $(OUT)
$(OUT): src/main.c tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Itools src/main.c -o $@ -Wl,-Map,$@.map
run: $(OUT)
	@PCE_RUN_FRAMES=90 PCE_HEADLESS="$(PCE_HEADLESS)" tools/run-pce-headless.sh run "$(OUT)"
trace: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/genre_trace.py --rom "$(OUT)" --elf "$(OUT).elf" --scenario tools/genre-scenario.json --output build/genre-trace.json
visual-test: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/visual_scenario.py --rom "$(OUT)" --scenario tools/visual-scenario.json --output build/visual-evidence.json
clean:
	rm -rf build
