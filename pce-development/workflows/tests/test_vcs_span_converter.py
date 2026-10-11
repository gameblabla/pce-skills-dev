"""VCS-inspired height-threshold conversion must preserve PCE paired-BAT pixels.

The reference algorithm is the old per-row visibility test. The candidate
walks the four top/bottom wall boundaries and emits constant-coverage spans.
No emulator or LLVM-MOS compiler is needed for these exhaustive host checks.
"""
from pathlib import Path
import random
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples/34-rendered-raycaster'
SOURCE = EXAMPLE / 'src/main.c'
VCS = ROOT / 'third_party/vcs-raycaster-reference'


def old_rows(first, count, lt, lh, rt, rh):
    return [((2 if lt <= y < lt+lh else 0) |
             (1 if rt <= y < rt+rh else 0)) for y in range(first, first+count)]


def span_rows(first, count, lt, lh, rt, rh):
    y = first
    limit = first + count
    result = []
    while y < limit:
        until = min([limit] + [edge for edge in (lt, lt+lh, rt, rt+rh) if y < edge < limit])
        coverage = (2 if lt <= y < lt+lh else 0) | (1 if rt <= y < rt+rh else 0)
        result.extend([coverage] * (until - y))
        y = until
    return result


def render_rows(flags, first):
    # Independent 4-bit pixel patterns to catch nibbles swapped by the new
    # compositor as well as visibility mistakes at the four span boundaries.
    return [((0xF2 << 8) | (((y * 7 + 3) & 15) << 4) | ((y * 3 + 1) & 15))
            if bits == 0 else
            ((0xF2 << 8) |
             (((y * 11 + 9) & 15) if (bits & 2) else ((y * 7 + 3) & 15)) << 4 |
             (((y * 13 + 5) & 15) if (bits & 1) else ((y * 3 + 1) & 15)))
            for y, bits in enumerate(flags, first)]


class VcsSpanConverterTests(unittest.TestCase):
    def test_every_height_transition_and_page_seam(self):
        for lt in (0, 1, 30, 31, 32, 62, 63, 64, 65, 100, 116):
            for lh in (0, 1, 12, 32, 64, 116, 128-lt):
                if lt+lh > 128: continue
                for rt in (0, 1, 30, 32, 62, 63, 64, 65, 100, 116):
                    for rh in (0, 1, 12, 32, 64, 116, 128-rt):
                        if rt+rh > 128: continue
                        for first, count in ((0, 128), (0, 64), (63, 3), (64, 64), (120, 8)):
                            self.assertEqual(span_rows(first,count,lt,lh,rt,rh),
                                             old_rows(first,count,lt,lh,rt,rh))

    def test_random_fragments_preserve_both_pixel_nibbles(self):
        rng = random.Random(2018)
        for _ in range(5000):
            lt, rt = rng.randrange(129), rng.randrange(129)
            lh, rh = rng.randrange(129-lt), rng.randrange(129-rt)
            first = rng.randrange(128)
            count = rng.randrange(1, 129-first)
            old = old_rows(first,count,lt,lh,rt,rh)
            new = span_rows(first,count,lt,lh,rt,rh)
            self.assertEqual(render_rows(new,first),render_rows(old,first))

    def test_source_has_both_reference_and_pce_span_paths(self):
        source = SOURCE.read_text()
        assert '#define RAY_VCS_SPAN_CONVERTER 1' in source
        self.assertIn('switch(coverage)', source)
        self.assertIn('if(lbottom>y && lbottom<until)', source)
        self.assertIn('if(rbottom>y && rbottom<until)', source)
        self.assertIn('#if RAY_VCS_SPAN_CONVERTER', source)
        self.assertIn('RAY_STAGE_LEFT_TEXEL', source)
        self.assertIn('RAY_STAGE_RIGHT_TEXEL', source)
        self.assertIn('pce_memop((void*)IO_VDC_DATA', source)
        self.assertIn('if(n>until_page)n=until_page;', source)
        self.assertIn('96u', source)

    def test_vcs_source_provenance_preserved(self):
        self.assertTrue((VCS / 'LICENSE').is_file())
        license_text = (VCS / 'LICENSE').read_text()
        self.assertIn('MIT License', license_text)
        self.assertIn('Guillaume Laudet', license_text)
        for name in ('raycast.asm','raycast_converter.asm','mul8.8x8.asm'):
            self.assertTrue((VCS / name).is_file())


if __name__ == '__main__':
    unittest.main()
