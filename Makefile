.DEFAULT_GOAL := help
PYTHON ?= python3
ROOT := pce-development
TOOL := $(ROOT)/workflows/offline.py
EX := $(ROOT)/examples
.PHONY: help doctor route project-check micro-lint micro-build games-build game-run hybrid-test trace-test test
help:
	@printf '%s\n' 'Offline PC Engine toolkit:' '  make doctor       - inspect compiler, emulator, BIOS env (no network)' '  make project-check - validate specs and game source rules' '  make micro-lint   - enforce no graphics in audio examples' '  make micro-build  - compile every tiny HuCard project' '  make games-build  - compile two standalone game projects' '  make game-run     - headless game smoke, needs PCE_HEADLESS' '  make hybrid-test  - input-driven ROM scene changes (newer RPC)' '  make trace-test   - platformer deterministic P2TR, needs PCE_HEADLESS' '  make test         - offline unit and source checks' '  python3 $(TOOL) route "platformer plus racing"'
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
games-build:
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
test: project-check micro-lint
	$(PYTHON) -m unittest discover -s $(ROOT)/workflows/tests -v
