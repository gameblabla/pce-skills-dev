.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
OUT := build/34-rendered-raycaster.pce
.PHONY: interaction-test interaction-replay all run trace visual-test clean
all: tables-check $(OUT)
$(OUT): src/main.c src/ray_tables.h tools/genre_trace.h | toolchain
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

# Deterministic collision/checkpoint acceptance; stores decoded frame evidence.
interaction-test: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/genre_trace.py --rom "$(OUT)" --elf "$(OUT).elf" --scenario tools/interaction-scenario.json --output build/interaction-report.json --samples-output build/interaction-frames.json
interaction-replay:
	python3 tools/genre_trace.py --trace build/interaction-frames.json --scenario tools/interaction-scenario.json --output build/interaction-replay.json

.PHONY: tables-check
tables-check:
	python3 tools/gen_ray_tables.py --check
