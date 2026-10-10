"""Compile the *vendored* HuC6280 profiler clock to catch native regressions.

No emulator, SDK, or ROM is required; skips gracefully without a C++ compiler.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HEADER = (Path(__file__).resolve().parents[2] / 'third_party' /
          'mednafenPceDev-main' / 'mednafen' / 'src' / 'pce')


@unittest.skipUnless(shutil.which('c++'), 'C++ compiler unavailable')
class NativeClockTests(unittest.TestCase):
    def test_physical_pc_frame_wrap_repeated_segments_and_block_transfer(self):
        source = r'''#include <stdint.h>
#include "cycle_profiler.h"
#include <assert.h>
int main() {
 using MDFN_IEN_PCE::CycleProfileClock;
 uint64_t *ticks = new uint64_t[1u << 21]();
 CycleProfileClock p;
 p.Instruction(ticks, 2, 0x123);
 p.Instruction(ticks, 6, 0x456);
 assert(ticks[0x123] == 4);
 // End frame clock is 11; next frame begins at the 0..11 carry.
 p.FrameEnd(ticks, 11, 1);
 assert(ticks[0x456] == 5);
 p.Instruction(ticks, 2, 0x777);
 assert(ticks[0x456] == 6);
 p.Instruction(ticks, 8, 0x123);
 assert(ticks[0x777] == 6);
 p.FrameEnd(ticks, 13, 1);
 assert(ticks[0x123] == 9);
 // A native block transfer can resume across multiple video-frame resets
 // without entering the normal opcode loop. Keep charging the *same* PC.
 p.Reset();
 p.Instruction(ticks, 1, 0xabc);
 p.FrameEnd(ticks, 100, 0);
 p.FrameEnd(ticks, 100, 0);
 p.Instruction(ticks, 12, 0xdef);
 assert(ticks[0xabc] == 211);
 // New RPC profiling window discards the previous PC/timestamp anchor.
 p.Reset();
 p.Instruction(ticks, 999, 0x123);
 p.Instruction(ticks, 1001, 0x456);
 assert(ticks[0xabc] == 211);
 assert(ticks[0x123] == 11);
 // An unexpected state-load timestamp rewind must never underflow.
 p.Instruction(ticks, 1, 0x345);
 assert(ticks[0x456] == 6);
 p.Instruction(ticks, 4, 0x567);
 assert(ticks[0x345] == 3);
 delete[] ticks;
}
'''
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'test.cpp'
            exe = Path(d) / 'test'
            src.write_text(source)
            subprocess.run(['c++', '-std=c++11', '-Wall', '-Wextra', '-Werror',
                            '-I', str(HEADER), str(src), '-o', str(exe)],
                           check=True, capture_output=True, text=True)
            subprocess.run([str(exe)], check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
