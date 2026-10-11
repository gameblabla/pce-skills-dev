"""Guard the optional VRAM buffer's memory map, DMA size, and release semantics."""
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
spec=importlib.util.spec_from_file_location('compare_vram_buffering',ROOT/'tools/compare_vram_buffering.py')
comparison=importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)

class BufferedBATTests(unittest.TestCase):
    def test_hidden_bitmap_does_not_overlap_visible_or_tile_patterns(self):
        active=(0x0000,0x2000)
        patterns=(0x2000,0x3000)
        hidden=(0x4000,0x6000)
        self.assertTrue(active[1]<=patterns[0]<patterns[1]<=hidden[0])
        self.assertEqual(hidden[1]-hidden[0],8192)
        self.assertLessEqual(hidden[1],0x8000)

    def test_two_bounded_word_dmas_and_no_false_page_flip_claim(self):
        src=(ROOT/'src/main.c').read_text()
        self.assertIn('RAY_VRAM_BACK_BASE 0x4000u',src)
        self.assertIn('piece<2u',src)
        self.assertIn('piece<<12',src)
        self.assertIn('),4096u)',src)
        self.assertIn('not an atomic full-frame swap',src.lower())
        readme=(ROOT/'README.md').read_text()
        self.assertIn('not an atomic double-buffer page flip',readme.lower())
        self.assertIn('Example implementation. Not speed optimized, has issues.',readme)

    def test_comparison_rejects_invalid_image_even_if_faster(self):
        old={'totals':{'video_frames':1080,'turning_views_per_second':2.167,
                       'changed_views':14,'vram_words':88000}}
        new={'totals':{'video_frames':1080,'turning_views_per_second':3.0,
                       'changed_views':24,'vram_words':90000}}
        with self.assertRaises(ValueError):
            comparison.compare(old,new,{'matched':False,'differing_pixels':1})
        result=comparison.compare(old,new,{'matched':True,'differing_pixels':0})
        self.assertTrue(result['passed'])
        self.assertEqual(result['buffered_additional_dma_words_per_present'],8192)
        self.assertEqual(result['buffered_dma_copies_per_present'],2)
        self.assertIn('not a tear-free atomic',result['caveat'])

if __name__=='__main__': unittest.main()
