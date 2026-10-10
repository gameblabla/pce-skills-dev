.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
OUT := build/29-visual-novel.pce
GEN := src/vn_assets.c src/vn_assets.h src/manifest.json
.PHONY: all assets assets-multi clean run debug trace model-check visual-test
all: $(OUT)
assets: $(GEN)
# Optional high-colour backgrounds: use 16 tile-local BG palettes (requires numpy).
assets-multi:
	python3 tools/vn_pack.py pack --background assets/background.png --closed assets/mouth_closed.png --open assets/mouth_open.png --out src --palette-mode multi
$(GEN) &: assets/background.png assets/mouth_closed.png assets/mouth_open.png tools/vn_pack.py
	python3 tools/vn_pack.py pack --background assets/background.png --closed assets/mouth_closed.png --open assets/mouth_open.png --out src
$(OUT): src/main.c $(GEN) tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Isrc -Itools src/main.c src/vn_assets.c -o $@ -Wl,--defsym=__rom_bank0=0x8000,--defsym=__rom_bank0_size=0x8000 -Wl,-Map,$@.map
run debug: $(OUT)
	@PCE_RUN_FRAMES="$(or $(PCE_RUN_FRAMES),120)" PCE_HEADLESS="$(PCE_HEADLESS)" PCE_RUN_SCREENSHOT="$(PCE_RUN_SCREENSHOT)" tools/run-pce-headless.sh "$@" "$(OUT)"
trace: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/genre_trace.py --rom "$(OUT)" --elf "$(OUT).elf" --scenario tools/vn-scenario.json --output build/genre-trace.json
visual-test: $(OUT)
	@PCE_RUN_FRAMES=108 PCE_HEADLESS="$(PCE_HEADLESS)" PCE_RUN_SCREENSHOT=build/mouth-closed.png tools/run-pce-headless.sh run "$(OUT)" >/dev/null
	@PCE_RUN_FRAMES=120 PCE_HEADLESS="$(PCE_HEADLESS)" PCE_RUN_SCREENSHOT=build/mouth-open.png tools/run-pce-headless.sh run "$(OUT)" >/dev/null
	python3 tools/vn_visual_check.py build/mouth-closed.png build/mouth-open.png --out build/visual-report.json
model-check:
	python3 tools/vn_pack.py pack --background assets/background.png --closed assets/mouth_closed.png --open assets/mouth_open.png --out build/verify-assets
clean:
	rm -rf build
