.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
OUT := build/32-racing-trace-probe.pce
.PHONY: all run trace clean
all: $(OUT)
$(OUT): src/main.c tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0 -Itools src/main.c -o $@ -Wl,-Map,$@.map
run: $(OUT)
	@PCE_RUN_FRAMES=80 PCE_HEADLESS="$(PCE_HEADLESS)" tools/run-pce-headless.sh run "$(OUT)"
trace: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/genre_trace.py --rom "$(OUT)" --elf "$(OUT).elf" --scenario tools/genre-scenario.json --output build/genre-trace.json
clean:
	rm -rf build
