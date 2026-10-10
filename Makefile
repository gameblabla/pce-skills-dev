.DEFAULT_GOAL := help
PYTHON ?= python3
ROOT := pce-development
TOOL := $(ROOT)/workflows/offline.py
EX := $(ROOT)/examples
.PHONY: help doctor route project-check micro-lint micro-build games-build game-run hybrid-test trace-test test
help:
	@printf '%s\n' 'Offline PC Engine toolkit:' '  make doctor       - inspect compiler, emulator, BIOS env (no network)' '  make project-check - validate specs and game source rules' '  make micro-lint   - enforce no graphics in audio examples' '  make micro-build  - compile every tiny HuCard project' '  make games-build  - compile two standalone game projects' '  make agent-check  - reject hallucinated SDK symbols and large inline assets' '  make agent-assets - validate tilemap generator + level JSON' '  make agent-build  - compile generated-map example' '  make game-run     - headless game smoke, needs PCE_HEADLESS' '  make hybrid-test  - input-driven ROM scene changes (newer RPC)' '  make trace-test   - platformer deterministic P2TR, needs PCE_HEADLESS' '  make genre-check  - offline G2TR schemas + visual-novel asset audits' '  make genre-build  - build G2TR probes + visual-novel example' '  make genre-test   - trace genres and verify visual novel mouth in emulator' '  make test         - offline unit and source checks' '  python3 $(TOOL) route "platformer plus racing"'
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
test: project-check micro-lint agent-check agent-assets genre-check
	$(PYTHON) -m unittest discover -s $(ROOT)/workflows/tests -v

# Offline local-AI failure gates (no download, API calls, or firmware).
.PHONY: agent-check agent-assets agent-build logs-help
agent-check:
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
genre-test: genre-build
	@for project in $(GENRE_PROBES); do $(MAKE) -C $(EX)/$$project trace || exit 1; done
	$(MAKE) -C $(EX)/29-visual-novel trace
	$(MAKE) -C $(EX)/29-visual-novel visual-test
