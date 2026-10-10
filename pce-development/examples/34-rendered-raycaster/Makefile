.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
PCE_FLAGS += -DBAT_BITMAP_NATIVE_IRQ
ATOMIC_FLAGS := -DBAT_BITMAP_DOUBLE_BUFFER=1 -DRAY_DOUBLE_BUFFER=1
OUT := build/34-rendered-raycaster.pce
.PHONY: interaction-test interaction-replay all run trace visual-test bitmap-test clean
all: tables-check $(OUT)
$(OUT): src/main.c src/bat_bitmap.h src/bat_bitmap_irq.S src/ray_tables.h tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -Itools src/main.c src/bat_bitmap_irq.S -o $@ -Wl,-Map,$@.map
PCE_RUN_FRAMES ?= 180
run: $(OUT)
	@PCE_RUN_FRAMES="$(PCE_RUN_FRAMES)" PCE_HEADLESS="$(PCE_HEADLESS)" tools/run-pce-headless.sh run "$(OUT)"
bitmap-test: run
	python3 tools/check_bitmap.py build/headless.png
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

# Same-source 4-row and 8-row HuC6280 TIA upload benchmarks. Both runs
# verify six actual emulator screenshots and count completed VRAM passes.
.PHONY: bitmap-stress bitmap-throughput
BASELINE_ROM := build/34-rendered-raycaster-four-row.pce
$(BASELINE_ROM): src/main.c src/bat_bitmap.h src/bat_bitmap_irq.S src/ray_tables.h tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_SLICE_ROWS=4 -DRAY_UPLOAD_TIA=1 -Itools src/main.c src/bat_bitmap_irq.S -o $@
bitmap-stress: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(OUT) --elf $(OUT).elf --output build/bitmap-stress.json
bitmap-throughput: $(OUT) $(BASELINE_ROM)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(BASELINE_ROM) --elf $(BASELINE_ROM).elf --output build/bitmap-baseline.json
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(OUT) --elf $(OUT).elf --output build/bitmap-optimized.json
	python3 tools/bitmap_compare.py --baseline build/bitmap-baseline.json --optimized build/bitmap-optimized.json --output build/bitmap-comparison.json

# PCEdev-style two half-pages: atomic VBlank BXR flip at 128x64 logical
# resolution, preserving 512x224 physical timing. Quality vs presentation
# is a CHOICE; the default remains full-detail 128x128 progressive BAT.
.PHONY: atomic-rom atomic-bitmap-test atomic-stress atomic-test
ATOMIC_ROM := build/34-rendered-raycaster-atomic-64.pce
$(ATOMIC_ROM): src/main.c src/bat_bitmap.h src/bat_bitmap_irq.S src/ray_tables.h tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) $(ATOMIC_FLAGS) -Itools src/main.c src/bat_bitmap_irq.S -o $@ -Wl,-Map,$@.map
atomic-rom: $(ATOMIC_ROM)
atomic-bitmap-test: $(ATOMIC_ROM)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/atomic_present.py --rom $(ATOMIC_ROM) --elf $(ATOMIC_ROM).elf --output build/atomic-evidence.json --frames 160
atomic-stress: $(ATOMIC_ROM)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(ATOMIC_ROM) --elf $(ATOMIC_ROM).elf --mode atomic --output build/atomic-stress.json
atomic-test: atomic-bitmap-test atomic-stress

.PHONY: presentation-compare
presentation-compare: bitmap-stress atomic-stress
	python3 tools/compare_presentation.py --full build/bitmap-stress.json --atomic build/atomic-stress.json --output build/presentation-comparison.json
