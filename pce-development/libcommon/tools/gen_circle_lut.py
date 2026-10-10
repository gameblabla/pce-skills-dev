#!/usr/bin/env python3
"""Build exact interior extents for x*x + y*y < 40*40 on the host."""
from math import isqrt
from pathlib import Path
r=[isqrt(1599 - y*y) for y in range(40)]
out='/* GENERATED - no target-side squared multiply. */\nstatic const uint8_t pce_circle_extent[40] = {\n'
for i in range(0,len(r),10):out+='    '+', '.join(map(str,r[i:i+10]))+',\n'
out+='};\n'
dest=Path(__file__).resolve().parents[1]/'src/circle_lut.h'
import sys
if '--check' in sys.argv:
    assert dest.read_text()==out,'stale circle lookup data'
else: dest.write_text(out)
