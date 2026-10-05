# Include this from every LLVM-MOS project Makefile. The helper uses a compiler
# already on PATH, or installs the pinned SDK into the user's local data dir.
PCE_SDK_MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PCE_SDK_BOOTSTRAP := $(PCE_SDK_MAKEFILE_DIR)llvm-mos-sdk.sh

LLVM_MOS_CC ?= mos-pce-clang

# Avoid downloading the SDK just to clean or print help. The default goal is a
# build, so a plain `make` prepares the compiler before any recipe runs.
PCE_SDK_GOALS := $(if $(strip $(MAKECMDGOALS)),$(MAKECMDGOALS),all)
PCE_SDK_BUILD_GOALS := $(filter-out clean help bios-check convert-assets,$(PCE_SDK_GOALS))

ifneq ($(strip $(PCE_SDK_BUILD_GOALS)),)
PCE_LLVM_MOS_BIN := $(shell LLVM_MOS_CC='$(LLVM_MOS_CC)' "$(PCE_SDK_BOOTSTRAP)" --ensure-bin)
ifeq ($(strip $(PCE_LLVM_MOS_BIN)),)
$(error LLVM-MOS SDK setup failed; see the bootstrap message above)
endif
export PATH := $(PCE_LLVM_MOS_BIN):$(PATH)
export LLVM_MOS_BIN_DIR := $(PCE_LLVM_MOS_BIN)
endif

.PHONY: toolchain
toolchain:
	@command -v "$(LLVM_MOS_CC)" >/dev/null || { printf '%s\n' 'LLVM-MOS compiler is not available on PATH' >&2; exit 1; }
	@printf 'LLVM-MOS compiler: '; command -v "$(LLVM_MOS_CC)"
	@$(LLVM_MOS_CC) --version | sed -n '1,2p'

.PHONY: bios-check
bios-check:
	@"$(PCE_SDK_MAKEFILE_DIR)check-pce-bios.sh"
