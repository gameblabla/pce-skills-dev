.DEFAULT_GOAL := help
PYTHON ?= python3
ROOT := pce-development
TOOL := $(ROOT)/workflows/offline.py
EX := $(ROOT)/examples
.PHONY: help doctor route project-check micro-lint micro-build games-build game-run hybrid-test trace-test test
help:
	@printf '%s\n' 'Offline PC Engine toolkit:' '  make doctor       - inspect compiler, emulator, BIOS env (no network)' '  make project-check - validate specs and game source rules' '  make micro-lint   - enforce no graphics in audio examples' '  make micro-build  - compile every tiny HuCard project' '  make games-build  - compile standalone game and rendered genre projects' '  make agent-check  - reject hallucinated SDK symbols and large inline assets' '  make agent-assets - validate tilemap generator + level JSON' '  make agent-build  - compile generated-map example' '  make game-run     - headless game smoke, needs PCE_HEADLESS' '  make hybrid-test  - input-driven ROM scene changes (newer RPC)' '  make trace-test   - platformer deterministic P2TR, needs PCE_HEADLESS' '  make genre-check  - offline G2TR schemas + visual-novel asset audits' '  make genre-build  - build G2TR probes + visual-novel example' '  make genre-test   - trace genres, rendered scenes and VN mouth in emulator' '  make visual-games-build - build actual shmup/raycaster/racing scenes' '  make visual-games-test - scripted input + screenshot evidence for 3 scenes' '  make raycaster-bitmap-test - verify 512x224 paired-BAT raycaster screenshot' '  make interaction-test - exercise projectile hits, wall blocking and racing laps' '  make interaction-replay - offline recheck of captured per-tick G2TR evidence' '  make sat-check - offline VDC sprite admission limits / priority'  '  make arith-check - reject new 32/64-bit math and libm/libgcc linking' '  make arith-build - link-audit Mode7, circle, and 4 arithmetic ROMs' '  make arith-audit-all - build and link-audit all 99 micro ROMs' '  make arith-games - audit rendered shmup/raycaster/racer + two platformer ELFs' '  make vram-check - validate generic and generated scene VRAM upload plans' '  make performance-check - run VRAM and 8/16-bit arithmetic source gates' '  make cycles-check - offline master-clock profiling / attribution tests' '  make cycles-ray - profile and enforce raycaster IRQ/render budgets (needs RPC emulator)' '  make cycles-all - profile platformer, raycaster, racer and Mode 7 ROMs' '  make platformer-test - 16-bit P4TR walk/jump + hybrid return-gameplay checks' '  make test         - offline unit and source checks' '  python3 $(TOOL) route "platformer plus racing"'
doctor:
	$(PYTHON) $(TOOL) doctor
project-check:
	$(PYTHON) $(ROOT)/workflows/map_audit.py $(ROOT)/workflows/specs/platforms.json
	$(PYTHON) $(ROOT)/workflows/animation_audit.py $(ROOT)/workflows/specs/animation.json
	$(PYTHON) $(TOOL) validate $(ROOT)/workflows/specs/hybrid.json
	$(PYTHON) $(ROOT)/workflows/source_lint.py
	$(PYTHON) $(TOOL) simulate $(ROOT)/workflows/specs/hybrid.json $(ROOT)/workflows/specs/quick-test.json
micro-lint:
	$(PYTHON) $(EX)/micro/check.py --lint-only
micro-build:
	$(PYTHON) $(EX)/micro/check.py
games-build: visual-games-build
	$(MAKE) -C $(EX)/28-generated-level
	$(MAKE) -C $(EX)/29-visual-novel
	$(MAKE) -C $(EX)/26-platformer-starter
	$(MAKE) -C $(EX)/27-platformer-racer
game-run: games-build
	$(MAKE) -C $(EX)/26-platformer-starter run
	$(MAKE) -C $(EX)/27-platformer-racer run
hybrid-test: games-build
	$(MAKE) -C $(EX)/27-platformer-racer hybrid-test
trace-test: games-build
	$(MAKE) -C $(EX)/26-platformer-starter trace
	$(MAKE) -C $(EX)/27-platformer-racer trace
test: project-check micro-lint agent-check agent-assets genre-check arith-check vram-check
	$(PYTHON) -m unittest discover -s $(ROOT)/workflows/tests -v

# Offline local-AI failure gates (no download, API calls, or firmware).
.PHONY: agent-check agent-assets agent-build logs-help
agent-check: arith-check
	$(PYTHON) $(ROOT)/workflows/model_guard.py scan $(EX)/26-platformer-starter
	$(PYTHON) $(ROOT)/workflows/model_guard.py scan $(EX)/27-platformer-racer
	$(PYTHON) $(ROOT)/workflows/model_guard.py scan $(EX)/28-generated-level
	$(PYTHON) $(ROOT)/workflows/model_guard.py scan $(EX)/29-visual-novel
agent-assets:
	$(PYTHON) $(ROOT)/workflows/assetpack.py $(ROOT)/workflows/specs/pce-level.json --check
	$(MAKE) -C $(EX)/28-generated-level assets-check
agent-build: agent-check agent-assets
	$(MAKE) -C $(EX)/28-generated-level
logs-help:
	@echo 'python3 pce-development/workflows/model_guard.py diagnose build.log'

# G2TR v2 adds a genre-neutral companion; P2TR v1 remains available unchanged.
.PHONY: genre-check genre-build genre-test
GENRE_PROBES := 30-shmup-trace-probe 31-raycaster-trace-probe 32-racing-trace-probe
genre-check:
	$(PYTHON) -m unittest discover -s $(ROOT)/workflows/tests -p 'test_genre_trace.py' -v
	$(PYTHON) -m unittest discover -s $(ROOT)/workflows/tests -p 'test_vn_pack.py' -v
	$(PYTHON) $(ROOT)/workflows/model_guard.py scan $(EX)/29-visual-novel
	@for project in $(GENRE_PROBES); do $(PYTHON) $(ROOT)/workflows/model_guard.py scan $(EX)/$$project || exit 1; done
genre-build:
	$(MAKE) -C $(EX)/29-visual-novel
	@for project in $(GENRE_PROBES); do $(MAKE) -C $(EX)/$$project || exit 1; done
genre-test: genre-build visual-games-test interaction-test
	@for project in $(GENRE_PROBES); do $(MAKE) -C $(EX)/$$project trace || exit 1; done
	$(MAKE) -C $(EX)/29-visual-novel trace
	$(MAKE) -C $(EX)/29-visual-novel visual-test

# Rendered, input-driven genre games supplement instrumentation-only probes.
.PHONY: visual-games-build visual-games-test
VISUAL_GAMES := 33-rendered-shmup 34-rendered-raycaster 35-rendered-racer
visual-games-build:
	@for project in $(VISUAL_GAMES); do $(MAKE) -C $(EX)/$$project || exit 1; done
visual-games-test: visual-games-build
	@for project in $(VISUAL_GAMES); do 	  $(MAKE) -C $(EX)/$$project trace || exit 1; 	  $(MAKE) -C $(EX)/$$project visual-test || exit 1; 	done

# Input-driven game-rule acceptance: requires the RPC-capable headless emulator.
.PHONY: interaction-test interaction-replay
interaction-test: visual-games-build
	@for project in $(VISUAL_GAMES); do $(MAKE) -C $(EX)/$$project interaction-test || exit 1; done
	$(MAKE) -C $(EX)/33-rendered-shmup combat-visual-test
interaction-replay:
	@for project in $(VISUAL_GAMES); do $(MAKE) -C $(EX)/$$project interaction-replay || exit 1; done

.PHONY: sat-check
sat-check:
	$(PYTHON) $(ROOT)/workflows/sat_budget.py $(ROOT)/workflows/specs/sat-admission.json --strict

# 8/16-bit arithmetic: sources are checked without SDK; link audit needs LLVM-MOS.
.PHONY: arith-check arith-build arith-map
ARITH_ROM_EXAMPLES := 85-bitmap-128-circle 86-mode7-bitmap-floor 95-cpu-mul8 96-cpu-div16by8 97-cpu-signed-mul 98-cpu-mode7-lookup
arith-check:
	$(PYTHON) $(ROOT)/workflows/arith_guard.py source $(EX)
	$(PYTHON) $(ROOT)/workflows/arith_guard.py source $(ROOT)/libcommon
	$(PYTHON) $(ROOT)/libcommon/tools/gen_mode7_lut.py --check
	$(PYTHON) $(ROOT)/libcommon/tools/gen_circle_lut.py --check
	$(PYTHON) $(EX)/34-rendered-raycaster/tools/gen_ray_tables.py --check
arith-build: arith-check
	@for project in $(ARITH_ROM_EXAMPLES); do \
	  $(MAKE) -C $(EX)/micro/$$project --no-print-directory || exit 1; \
	  $(PYTHON) $(ROOT)/workflows/arith_guard.py elf $(EX)/micro/$$project/build/$$project.pce.elf || exit 1; \
	done

.PHONY: arith-audit-all
arith-audit-all: micro-build arith-check
	$(PYTHON) $(ROOT)/workflows/arith_guard.py audit $(EX)/micro --min-roms 99

# Five rendered game starters are now helper-free, including both Q4 platformers.
# P4TR v4 replaces the previous wide P2TR state ABI in examples 26 and 27.
.PHONY: arith-games vram-check performance-check
arith-games: visual-games-build
	@for project in $(VISUAL_GAMES); do \
	  $(PYTHON) $(ROOT)/workflows/arith_guard.py elf $(EX)/$$project/build/$$project.pce.elf || exit 1; \
	done
	@for project in 26-platformer-starter 27-platformer-racer; do \
	  $(MAKE) -C $(EX)/$$project --no-print-directory || exit 1; \
	  $(PYTHON) $(ROOT)/workflows/arith_guard.py elf $(EX)/$$project/build/$$project.pce.elf || exit 1; \
	done
vram-check:
	$(PYTHON) $(ROOT)/workflows/vram_budget.py $(ROOT)/workflows/specs/vram-streaming.json --strict
	$(PYTHON) $(ROOT)/workflows/scene_vram.py $(EX)/33-rendered-shmup
	$(PYTHON) $(ROOT)/workflows/scene_vram.py $(EX)/35-rendered-racer
performance-check: arith-check vram-check

# 16-bit movement + independent external collision geometry. This catches
# regressions beyond a simple display/scene switch screenshot.
.PHONY: platformer-check platformer-test platformer-replay
platformer-check:
	$(PYTHON) -m unittest discover -s $(ROOT)/workflows/tests -p 'test_p4*.py' -v
platformer-test: platformer-check
	$(MAKE) -C $(EX)/26-platformer-starter trace
	$(MAKE) -C $(EX)/27-platformer-racer trace
	$(MAKE) -C $(EX)/27-platformer-racer trace-hybrid
	$(MAKE) -C $(EX)/27-platformer-racer hybrid-test
platformer-replay:
	$(MAKE) -C $(EX)/26-platformer-starter trace-replay
	$(MAKE) -C $(EX)/27-platformer-racer trace-hybrid-replay

# Optional measured instruction comparison against an existing LOCAL checkout.
# Do not interpret the total-instruction delta as FPS/cycles: idle wait is included.
.PHONY: platformer-perf
platformer-perf:
	@test -n "$(PCE_BASELINE_ROOT)" && test -n "$(PCE_HEADLESS)" || { echo 'Usage: PCE_BASELINE_ROOT=/path/to/old-checkout PCE_HEADLESS=/path/to/pce-headless make platformer-perf' >&2; exit 2; }
	$(PYTHON) $(ROOT)/workflows/perf_pair.py --baseline "$(PCE_BASELINE_ROOT)" --emulator "$(PCE_HEADLESS)" --out build/platformer-perf

# Specific regression: no return to 8px BAT wall columns or black frames.
.PHONY: raycaster-bitmap-test
raycaster-bitmap-test:
	$(MAKE) -C $(EX)/34-rendered-raycaster bitmap-test

# Real emulated HuC6280 master-clock profiling by physical ROM symbol. Unlike
# --cov instruction counts, this attributes per-instruction elapsed bus/CPU
# master ticks to the linked .mlb's physical offsets. Never claim real-hardware
# speedup from these emulator reports.
.PHONY: cycles-check cycles-ray cycles-all
CYCLE_TOOL := $(ROOT)/workflows/cycle_profile.py
CYCLE_SPECS := $(ROOT)/workflows/specs/cycles
cycles-check:
	$(PYTHON) -m unittest discover -s $(ROOT)/workflows/tests -p 'test_cycle_profile.py' -v
cycles-ray:
	@test -n "$(PCE_HEADLESS)" && test -x "$(PCE_HEADLESS)" || { echo 'Set PCE_HEADLESS=/absolute/path/to/RPC-capable/pce-headless' >&2; exit 2; }
	$(MAKE) -C $(EX)/34-rendered-raycaster all
	$(PYTHON) $(CYCLE_TOOL) run --emulator "$(PCE_HEADLESS)" --rom $(EX)/34-rendered-raycaster/build/34-rendered-raycaster.pce --mlb $(EX)/34-rendered-raycaster/build/34-rendered-raycaster.mlb --scenario $(CYCLE_SPECS)/raycaster.json --out build/cycles/raycaster
	$(PYTHON) $(CYCLE_TOOL) gate --report build/cycles/raycaster/report.json --budget $(CYCLE_SPECS)/raycaster-budget.json
cycles-all: cycles-ray
	$(MAKE) -C $(EX)/26-platformer-starter all
	$(MAKE) -C $(EX)/35-rendered-racer all
	$(MAKE) -C $(EX)/micro/86-mode7-bitmap-floor all
	$(PYTHON) $(CYCLE_TOOL) run --emulator "$(PCE_HEADLESS)" --rom $(EX)/26-platformer-starter/build/26-platformer-starter.pce --mlb $(EX)/26-platformer-starter/build/26-platformer-starter.mlb --scenario $(CYCLE_SPECS)/platformer.json --out build/cycles/platformer
	$(PYTHON) $(CYCLE_TOOL) run --emulator "$(PCE_HEADLESS)" --rom $(EX)/35-rendered-racer/build/35-rendered-racer.pce --mlb $(EX)/35-rendered-racer/build/35-rendered-racer.mlb --scenario $(CYCLE_SPECS)/racer.json --out build/cycles/racer
	$(PYTHON) $(CYCLE_TOOL) run --emulator "$(PCE_HEADLESS)" --rom $(EX)/micro/86-mode7-bitmap-floor/build/86-mode7-bitmap-floor.pce --mlb $(EX)/micro/86-mode7-bitmap-floor/build/86-mode7-bitmap-floor.mlb --scenario $(CYCLE_SPECS)/mode7.json --out build/cycles/mode7
	$(PYTHON) $(CYCLE_TOOL) gate --report build/cycles/mode7/report.json --budget $(CYCLE_SPECS)/mode7-budget.json
