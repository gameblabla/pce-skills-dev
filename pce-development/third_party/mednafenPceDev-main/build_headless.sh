#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT/mednafen"

./configure \
  --enable-libxxx-mode \
  --enable-debugger \
  --enable-pce \
  --disable-pce-fast \
  --disable-apple2 \
  --disable-gb \
  --disable-gba \
  --disable-lynx \
  --disable-md \
  --disable-nes \
  --disable-ngp \
  --disable-pcfx \
  --disable-psx \
  --disable-sasplay \
  --disable-sms \
  --disable-snes \
  --disable-snes-faust \
  --disable-ss \
  --disable-ssfplay \
  --disable-vb \
  --disable-wswan \
  --disable-alsa \
  --disable-jack \
  --without-libflac

JOBS=${JOBS:-2}
make -j"$JOBS"
cp -f src/mednafen "$ROOT/pce-headless"
printf 'Built PCE headless emulator at %s\n' "$ROOT/pce-headless"
