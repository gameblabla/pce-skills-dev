"""128x128 paired-BAT layout and removal regression tests."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('paired_bat_plan',ROOT/'paired_bat_plan.py')
plan=importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)
EX=ROOT.parent/'examples/34-rendered-raycaster'

class PairedBatPlanTests(unittest.TestCase):
    def test_full_covers_all_8192_words_after_seam_rotation(self):
        p=plan.plan('full')
        self.assertEqual(p['logical_pixels'],[128,128])
        self.assertEqual(p['bytes_per_page'],16384)
        self.assertEqual(p['batches_per_complete_image'],16)
        self.assertEqual(p['presentation'],'progressive-bat')
        addresses={plan.word_address(y,x) for y in range(128) for x in range(64)}
        self.assertEqual(addresses,set(range(8192)))
        self.assertEqual(plan.word_address(63,0),63*128)
        self.assertEqual(plan.word_address(64,0),63*128+64)
        self.assertEqual(plan.word_address(65,0),64)
    def test_no_second_framebuffer_or_atomic_build(self):
        for kw in ({'mode':'full','page':1},{'mode':'atomic','page':0}):
            with self.assertRaises(ValueError):plan.word_address(1,0,**kw)
        with self.assertRaises(ValueError):plan.plan('atomic')
        mk=(EX/'Makefile').read_text()
        self.assertNotIn('atomic-rom',mk)
        self.assertNotIn('ATOMIC_FLAGS',mk)
        self.assertFalse((EX/'tools/atomic_present.py').exists())
        source=(EX/'src/main.c').read_text()
        self.assertNotIn('RAY_DOUBLE_BUFFER',source)
        self.assertIn('Example implementation. Not speed optimized, has issues.',source)
    def test_invalid_rows_columns_and_batch_sizes(self):
        for y,x in [(-1,0),(128,0),(0,64)]:
            with self.assertRaises(ValueError):plan.word_address(y,x)
        for b in (3,12,16):
            with self.assertRaises(ValueError):plan.plan('full',batch_rows=b)

if __name__=='__main__':unittest.main()
