.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
include tools/llvm-mos-sdk.mk
PCE_FLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -mlto-zp=0
PCE_FLAGS += -DBAT_BITMAP_NATIVE_IRQ
ATOMIC_FLAGS := -DBAT_BITMAP_DOUBLE_BUFFER=1 -DRAY_DOUBLE_BUFFER=1
OUT := build/34-rendered-raycaster.pce
# Full-detail ROM uses 32 KiB of contiguous HuCard ROM: the 16 KiB static
# BAT backdrop lives in ROM, never in scarce HuC6280 working RAM. Atomic
# and reference renderers deliberately keep their original 8 KiB layout.
FAST_ROM_LINK := -Wl,--defsym=__rom_bank0=0x8000,--defsym=__rom_bank0_size=0x8000
# The 128-ray tables no longer fit the old 8KiB row/atomic prototypes.
# Keep reference and atomic variants in a contiguous 16KiB HuCard bank.
ROW_ROM_LINK := -Wl,--defsym=__rom_bank0=0xc000,--defsym=__rom_bank0_size=0x4000
.PHONY: interaction-test interaction-replay all run trace visual-test bitmap-test clean
all: tables-check $(OUT)
$(OUT): src/main.c src/bat_bitmap.h src/bat_sparse_irq.S src/ray_tables.h src/wall_pairs.h src/backdrop_words.h src/wall_codegen.S src/sheet_pairs.h src/hires_texels.h src/sheet_palette.h assets/wolftextures16.png tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_STAGE_UPLOAD=1 -DRAY_WALL_CODEGEN=0 -Itools src/main.c src/bat_sparse_irq.S -o $@ $(FAST_ROM_LINK) -Wl,-Map,$@.map
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
	python3 tools/check_128_rays.py
	python3 tools/gen_wall_pairs.py --check
	python3 tools/gen_backdrop.py --check
	python3 tools/gen_sparse_irq.py --check
	python3 tools/gen_texture_sheet.py --check
	python3 tools/gen_wall_codegen.py --check

# Same-source 4-row and 8-row HuC6280 TIA upload benchmarks. Both runs
# verify six actual emulator screenshots and count completed VRAM passes.
.PHONY: bitmap-stress bitmap-throughput
BASELINE_ROM := build/34-rendered-raycaster-four-row.pce
$(BASELINE_ROM): src/main.c src/bat_bitmap.h src/bat_bitmap_irq.S src/ray_tables.h src/wall_pairs.h tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_COLUMN_STREAM=0 -DRAY_FAST_SPANS=0 -DRAY_SLICE_ROWS=4 -DRAY_UPLOAD_TIA=1 -Itools src/main.c src/bat_bitmap_irq.S -o $@ $(ROW_ROM_LINK)
bitmap-stress: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(OUT) --elf $(OUT).elf --mode column --output build/bitmap-stress.json
bitmap-throughput: column-benchmark
	@echo "NOTE: Column dirty views and old complete BAT passes are different work; no false full-redraw speedup ratio."

# PCEdev-style two half-pages: atomic VBlank BXR flip at 128x64 logical
# resolution, preserving 512x224 physical timing. Quality vs presentation
# is a CHOICE; the default remains full-detail 128x128 progressive BAT.
.PHONY: atomic-rom atomic-bitmap-test atomic-stress atomic-test
ATOMIC_ROM := build/34-rendered-raycaster-atomic-64.pce
$(ATOMIC_ROM): src/main.c src/bat_bitmap.h src/bat_bitmap_irq.S src/ray_tables.h src/wall_pairs.h tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) $(ATOMIC_FLAGS) -DRAY_FAST_SPANS=0 -Itools src/main.c src/bat_bitmap_irq.S -o $@ $(ROW_ROM_LINK) -Wl,-Map,$@.map
atomic-rom: $(ATOMIC_ROM)
atomic-bitmap-test: $(ATOMIC_ROM)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/atomic_present.py --rom $(ATOMIC_ROM) --elf $(ATOMIC_ROM).elf --output build/atomic-evidence.json --frames 160
atomic-stress: $(ATOMIC_ROM)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(ATOMIC_ROM) --elf $(ATOMIC_ROM).elf --mode atomic --output build/atomic-stress.json
atomic-test: atomic-bitmap-test atomic-stress

.PHONY: presentation-compare
presentation-compare: bitmap-stress atomic-stress
	python3 tools/compare_presentation.py --full build/bitmap-stress.json --atomic build/atomic-stress.json --output build/presentation-comparison.json

# Identical scene/geometry with the original branch-per-texel shader. This is
# for controlled throughput comparisons, NOT an atomic renderer variant.
.PHONY: wall-reference-rom wall-lookup-check
WALL_REFERENCE_ROM := build/34-rendered-raycaster-wall-reference.pce
$(WALL_REFERENCE_ROM): src/main.c src/bat_bitmap.h src/bat_bitmap_irq.S src/ray_tables.h src/wall_pairs.h tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_COLUMN_STREAM=0 -DRAY_FAST_SPANS=0 -DRAY_WALL_LOOKUP=0 -Itools src/main.c src/bat_bitmap_irq.S -o $@ $(ROW_ROM_LINK) -Wl,-Map,$@.map
wall-reference-rom: $(WALL_REFERENCE_ROM)
wall-lookup-check: tables-check
	python3 tools/verify_wall_pairs.py

# Compare TWO 128x128 full-detail ROMs (legacy branch shader vs paired
# lookup). The 128x64 atomic variant is deliberately excluded; redraws
# with half the pixels are not comparable. Both require six checked PNGs.
.PHONY: wall-lookup-throughput
wall-lookup-throughput: column-benchmark
	@echo "NOTE: use the ROM's changed-view and VRAM-word counters. The old full-redraw shader is not equivalent work."

# Bit-identical stationary emulator pixels from the two SAME-RESOLUTION builds;
# a screenshot being "textured" alone is insufficient to prove equivalence.
.PHONY: wall-lookup-visual
wall-lookup-visual: $(OUT) codegen-reference wall-lookup-check
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/wall_equivalence.py --reference $(CODEGEN_REFERENCE) --optimized $(OUT) --output build/wall-lookup-exact.json

# New full-detail VRAM-resident raycaster acceptance: verifies real changed
# columns, render state, long controller exercise, and bounded raster IRQ.
.PHONY: column-benchmark column-regression
column-benchmark: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/column_benchmark.py --rom $(OUT) --elf $(OUT).elf --output build/column-benchmark.json
column-regression: $(OUT) tables-check
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(OUT) --elf $(OUT).elf --mode column --output build/column-stress.json
	$(MAKE) column-benchmark
	$(MAKE) raster-sweep

# Validate HuC6280 immediate-ST0 address selection against the SDK VDC
# helper without changing resolution, bitmap words, or the raster schedule.
.PHONY: vdc-inline-visual
VDC_SDK_ROM := build/34-rendered-raycaster-sdk-vdc.pce
$(VDC_SDK_ROM): src/main.c src/bat_sparse_irq.S src/ray_tables.h src/hires_texels.h src/backdrop_words.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_STAGE_UPLOAD=1 -DRAY_WALL_CODEGEN=0 -DRAY_INLINE_VDC_ADDRESS=0 -Itools src/main.c src/bat_sparse_irq.S -o $@ $(FAST_ROM_LINK)
vdc-inline-visual: $(OUT) $(VDC_SDK_ROM)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/wall_equivalence.py --reference $(VDC_SDK_ROM) --optimized $(OUT) --output build/vdc-inline-equivalence.json

# Compare the center-first responsive presentation against the exact same
# source with the historical left-to-right column order. Same 128x128 pixels.
.PHONY: center-latency
CENTER_LINEAR_ROM := build/34-rendered-raycaster-linear-order.pce
$(CENTER_LINEAR_ROM): src/main.c src/bat_sparse_irq.S src/ray_tables.h src/hires_texels.h src/backdrop_words.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_STAGE_UPLOAD=1 -DRAY_WALL_CODEGEN=0 -DRAY_CENTER_FIRST=0 -Itools src/main.c src/bat_sparse_irq.S -o $@ $(FAST_ROM_LINK)
center-latency: $(OUT) $(CENTER_LINEAR_ROM)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/center_latency.py --linear-rom $(CENTER_LINEAR_ROM) --center-rom $(OUT) --output build/center-latency.json

.PHONY: raster-sweep
raster-sweep: $(OUT)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/raster_sweep.py --rom $(OUT) --elf $(OUT).elf --output build/raster-sweep.json

# Two same-resolution dirty-column versions: generated HuC6280 unrolled wall
# writes vs the existing C/TIA loop. Atomic remains a separate build.
.PHONY: codegen-reference codegen-benchmark
CODEGEN_REFERENCE := build/34-rendered-raycaster-column-reference.pce
$(CODEGEN_REFERENCE): src/main.c src/bat_bitmap.h src/bat_sparse_irq.S src/ray_tables.h src/wall_pairs.h src/sheet_pairs.h src/sheet_palette.h src/backdrop_words.h tools/genre_trace.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_WALL_CODEGEN=0 -Itools src/main.c src/bat_sparse_irq.S -o $@ $(FAST_ROM_LINK) -Wl,-Map,$@.map
codegen-reference: $(CODEGEN_REFERENCE)
codegen-benchmark: $(OUT) $(CODEGEN_REFERENCE)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/compare_codegen.py --reference $(CODEGEN_REFERENCE) --optimized $(OUT) --output build/codegen-comparison.json

# Same artwork and code paths, only the native VDC address setup differs.
# Do not compare against old synthetic textures as a speed claim.
SHEET_SLOW_ROM := build/34-rendered-raycaster-sheet-legacy-setup.pce
$(SHEET_SLOW_ROM): src/main.c src/bat_sparse_irq.S src/wall_codegen.S src/sheet_pairs.h src/sheet_palette.h src/backdrop_words.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_CODEGEN_FAST_SETUP=0 -Itools src/main.c src/bat_sparse_irq.S src/wall_codegen.S -o $@ $(FAST_ROM_LINK) -Wl,-Map,$@.map
.PHONY: sheet-textures-check sheet-fps-check
sheet-textures-check:
	python3 tools/gen_texture_sheet.py --check
	python3 tools/sgx_texture_plan.py --check
	python3 tools/gen_wall_codegen.py --check
	python3 tools/gen_backdrop.py --check
sheet-fps-check: $(OUT) $(SHEET_SLOW_ROM) sheet-textures-check
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/sheet_benchmark.py --reference $(SHEET_SLOW_ROM) --optimized $(OUT) --output build/sheet-native-setup-comparison.json

.PHONY: sheet-native-fps sheet-art-sgx
sheet-native-fps: sheet-fps-check
sheet-art-sgx: sheet-textures-check
	@echo "SGX preview/plane assets verified offline; there is NO tested SGX 2-VDC runtime ROM."

# Full-detail only: small irregular wall gaps are written directly through the
# VDC, avoiding TIA setup. The C/TIA fallback is an actual separate ROM with
# the *same texture sheet*, geometry and generated eight-word wall routines.
# Atomic (128x64) remains independent and is not part of the FPS comparison.
.PHONY: scalar-reference scalar-fps
SCALAR_REFERENCE := build/34-rendered-raycaster-scalar-tia-reference.pce
$(SCALAR_REFERENCE): src/main.c src/bat_sparse_irq.S src/wall_codegen.S src/ray_tables.h src/sheet_pairs.h src/backdrop_words.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_COLUMN_TIA=1 -DRAY_CANONICAL_WALL_KEY=0 -Itools src/main.c src/bat_sparse_irq.S src/wall_codegen.S -o $@ $(FAST_ROM_LINK) -Wl,-Map,$@.map
scalar-reference: $(SCALAR_REFERENCE)
scalar-fps: $(OUT) $(SCALAR_REFERENCE) tables-check
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/compare_scalar.py --reference $(SCALAR_REFERENCE) --optimized $(OUT) --output build/scalar-fps-comparison.json

# VCS-inspired height-threshold PCE converter. The independent legacy build
# proves exact paired-BAT textures and same-work dirty-view accounting.
.PHONY: vcs-span-check
VCS_SPAN_REFERENCE := build/34-rendered-raycaster-vcs-reference.pce
$(VCS_SPAN_REFERENCE): src/main.c src/bat_sparse_irq.S src/backdrop_words.h src/sheet_pairs.h src/hires_texels.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_STAGE_UPLOAD=1 -DRAY_WALL_CODEGEN=0 -DRAY_VCS_SPAN_CONVERTER=0 -Itools src/main.c src/bat_sparse_irq.S -o $@ $(FAST_ROM_LINK) -Wl,-Map,$@.map
vcs-span-check: $(OUT) $(VCS_SPAN_REFERENCE)
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/wall_equivalence.py --reference $(VCS_SPAN_REFERENCE) --optimized $(OUT) --output build/vcs-span-visual.json
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/column_benchmark.py --rom $(VCS_SPAN_REFERENCE) --elf $(VCS_SPAN_REFERENCE).elf --output build/vcs-span-reference-benchmark.json
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/column_benchmark.py --rom $(OUT) --elf $(OUT).elf --output build/vcs-span-optimized-benchmark.json
	python3 tools/compare_vcs_span.py --baseline build/vcs-span-reference-benchmark.json --span build/vcs-span-optimized-benchmark.json --visual build/vcs-span-visual.json --output build/vcs-span-comparison.json

# Experimental VCS-style cell grid-crossing and provably empty two-step jumps.
# The default renderer remains the established bit-exact Q8 marcher because
# same-work benchmarks have not established a measurable FPS improvement.
.PHONY: grid-crossing-rom grid-crossing-check
GRID_CROSS_ROM := build/34-rendered-raycaster-grid-crossing.pce
$(GRID_CROSS_ROM): src/main.c src/bat_sparse_irq.S src/ray_tables.h src/hires_texels.h src/backdrop_words.h | toolchain
	@mkdir -p build
	$(LLVM_MOS_CC) $(PCE_FLAGS) -DRAY_STAGE_UPLOAD=1 -DRAY_WALL_CODEGEN=0 -DRAY_GRID_CROSSING=1 -Itools src/main.c src/bat_sparse_irq.S -o $@ $(FAST_ROM_LINK) -Wl,-Map,$@.map
grid-crossing-rom: $(GRID_CROSS_ROM)
grid-crossing-check: $(OUT) $(GRID_CROSS_ROM)
	python3 -m unittest discover -s ../../workflows/tests -p 'test_ray_grid_crossing.py'
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/wall_equivalence.py --reference $(OUT) --optimized $(GRID_CROSS_ROM) --output build/grid-crossing-visual.json
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/column_benchmark.py --rom $(OUT) --elf $(OUT).elf --output build/grid-crossing-default-benchmark.json
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/column_benchmark.py --rom $(GRID_CROSS_ROM) --elf $(GRID_CROSS_ROM).elf --output build/grid-crossing-experimental-benchmark.json
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/raster_sweep.py --rom $(GRID_CROSS_ROM) --elf $(GRID_CROSS_ROM).elf --output build/grid-crossing-raster.json
	PCE_HEADLESS="$(PCE_HEADLESS)" python3 tools/bitmap_stress.py --rom $(GRID_CROSS_ROM) --elf $(GRID_CROSS_ROM).elf --mode column --output build/grid-crossing-stress.json
	python3 tools/compare_grid_crossing.py --reference build/grid-crossing-default-benchmark.json --experimental build/grid-crossing-experimental-benchmark.json --visual build/grid-crossing-visual.json --raster build/grid-crossing-raster.json --stress build/grid-crossing-stress.json --output build/grid-crossing-evidence.json
