"""Offline invariants for the fast, VRAM-resident full-detail raycaster."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
TOOLS=ROOT/'tools'
sys.path.insert(0,str(TOOLS))
import gen_backdrop
import gen_sparse_irq
import column_benchmark

class ColumnStreamTests(unittest.TestCase):
    def test_background_is_precomputed_and_deterministic(self):
        self.assertEqual((ROOT/'src/backdrop_words.h').read_text(),gen_backdrop.generate())
        # Exactly 8192 physical BAT words = complete 128x128 logical image.
        self.assertEqual(gen_backdrop.generate().count('0xf2'),8192)

    def test_sparse_irq_is_host_generated_and_schedules_127_changes(self):
        self.assertEqual((ROOT/'src/bat_sparse_irq.S').read_text(),gen_sparse_irq.gen())
        lines=[(y*7+3)//4 for y in range(1,128)]
        self.assertEqual(len(lines),127)
        self.assertEqual(lines[:4],[2,4,6,7])
        self.assertEqual(lines[-1],223)
        self.assertEqual(len(lines),len(set(lines)))
        self.assertEqual(sum(1 for y in range(128) if y==64),1)
        self.assertNotIn('st2 #2\n.Lno_page:',gen_sparse_irq.gen().split('cpy #64')[0])

    def test_vertical_vram_increment_and_short_irq_masks(self):
        src=(ROOT/'src/main.c').read_text()
        self.assertIn('VDC_CONTROL_VRAM_ADD_128',src)
        self.assertIn('RAY_COLUMN_CHUNK_WORDS 8u',src)
        self.assertIn('column_pass_dirty',src)
        self.assertIn('ray_bat_words',src)
        self.assertIn('if(cast_valid && cast_angle==angle',src)
        self.assertIn('pce_cpu_irq_enable();',src)
        make=(ROOT/'Makefile').read_text()
        self.assertIn('src/bat_sparse_irq.S',make)
        self.assertIn('src/bat_bitmap_irq.S',make) # atomic/reference remain independent
        self.assertIn('__rom_bank0_size=0x8000',make)

    def sample(self):
        result=[]
        for name,frames,buttons in column_benchmark.SCENARIO:
            result.append({'segment':name,'emulator_frames':frames,
                           'buttons':list(buttons),'dirty_views':0,'vram_words':0,
                           'game_updates':frames//2,'screenshot_colors':12})
        for n in ('turn-right','walk','turn-left'):
            x=next(s for s in result if s['segment']==n)
            x['dirty_views']=5;x['vram_words']=4000
        return result

    def test_real_dirty_view_accounting(self):
        report=column_benchmark.validate(self.sample())
        self.assertTrue(report['passed'])
        self.assertEqual(report['changed_views'],15)
        self.assertEqual(report['turning_views_per_second'],round(10*60/180,3))

    def test_rejects_fake_frame_without_actual_vram_writes(self):
        rows=self.sample();rows[1]['vram_words']=0
        with self.assertRaisesRegex(ValueError,'fabricated'):column_benchmark.validate(rows)

    def test_rejects_idle_only_fake_speed(self):
        rows=self.sample();rows[-1]['dirty_views']=2;rows[-1]['vram_words']=500
        with self.assertRaisesRegex(ValueError,'fully settled idle'):column_benchmark.validate(rows)

    def test_rejects_blank_screenshot_or_stalled_game(self):
        rows=self.sample();rows[1]['screenshot_colors']=1
        with self.assertRaisesRegex(ValueError,'unrendered'):column_benchmark.validate(rows)
        rows=self.sample();rows[1]['game_updates']=0
        with self.assertRaisesRegex(ValueError,'stalled'):column_benchmark.validate(rows)

    def test_rejects_missing_turns(self):
        rows=self.sample();rows[1]['dirty_views']=1
        with self.assertRaisesRegex(ValueError,'rotation failed'):column_benchmark.validate(rows)

if __name__=='__main__':unittest.main()
