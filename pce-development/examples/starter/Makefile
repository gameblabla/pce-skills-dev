# Copy this Makefile and the files in tools/ into a new project.
# Add project-specific build rules after verifying its LLVM-MOS SDK inputs.
.DEFAULT_GOAL := all

LLVM_MOS_CC ?= mos-pce-clang

include tools/llvm-mos-sdk.mk

.PHONY: all clean
all: toolchain

clean:
	@rm -rf build
