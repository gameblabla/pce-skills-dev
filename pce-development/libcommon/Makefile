.DEFAULT_GOAL := all
LLVM_MOS_CC ?= mos-pce-clang
LLVM_AR ?= llvm-ar
CFLAGS ?= -std=gnu11 -Os -Wall -Wextra -Werror -Iinclude
SRC := $(wildcard src/*.c)
OBJ := $(patsubst src/%.c,build/%.o,$(SRC))
OUT := build/libpcecommon.a
.PHONY: all clean tables-check
all: $(OUT)
build/%.o: src/%.c $(wildcard src/*_lut.h) include/pce_fastmath.h
	@mkdir -p build
	$(LLVM_MOS_CC) $(CFLAGS) -c $< -o $@
$(OUT): $(OBJ)
	$(LLVM_AR) rcs $@ $(OBJ)
tables-check:
	python3 tools/gen_mode7_lut.py --check
	python3 tools/gen_circle_lut.py --check
clean:
	rm -rf build
