.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
OUT := build/33-rendered-shmup.pce
GEN := src/scene_assets.c src/scene_assets.h src/scene_manifest.json
.PHONY: all assets assets-check run trace visual-test clean
all: $(OUT)
assets: $(GEN)
$(GEN) &: assets/background.png assets/sprites.png tools/scene_pack.py
	python3 tools/scene_pack.py pack --background assets/background.png --sprites assets/sprites.png --out src
assets-check:
	python3 tools/scene_pack.py pack --background assets/background.png --sprites assets/sprites.png --out build/asset-check
$(OUT): src/main.c $(GEN) tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Isrc -Itools src/main.c src/scene_assets.c -o $@ -Wl,-Map,$@.map
run: $(OUT)
	@PCE_RUN_FRAMES=90 PCE_HEADLESS="$(PCE_HEADLESS)" tools/run-pce-headless.sh run "$(OUT)"
trace: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/genre_trace.py --rom "$(OUT)" --elf "$(OUT).elf" --scenario tools/genre-scenario.json --output build/genre-trace.json
visual-test: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/visual_scenario.py --rom "$(OUT)" --output build/visual-evidence.json --scenario tools/visual-scenario.json
clean:
	rm -rf build
