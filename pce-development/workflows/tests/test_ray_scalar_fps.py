"""Cross-check wall-image dirty keys and new renderer FPS guard offline."""
import importlib.util
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
sys.path.insert(0,str(ROOT/'tools'))
import compare_scalar
import column_benchmark
import gen_ray_tables

class ScalarFPSChecks(unittest.TestCase):
    def test_canonical_wall_key_is_visually_equivalent_across_all_depths(self):
        # Depth is NOT independently visible: wall height determines top and
        # the exact V texture lookup; style already contains distance shading.
        heights=[max(12,min(116,360//(d+2))) for d in range(33)]
        v_tables=[[((k*32)//h if (k*2)<h else 0) for k in range(64)] for h in heights]
        for a in range(33):
            for b in range(33):
                if heights[a]==heights[b]:
                    self.assertEqual((128-heights[a])//2,(128-heights[b])//2)
                    self.assertEqual(v_tables[a],v_tables[b])
        self.assertTrue(any(a!=b and heights[a]==heights[b] for a in range(33) for b in range(33)))

    def test_cycle_gate_keeps_actual_renderer_cost_enforced(self):
        import json
        budget=json.loads((ROOT.parents[1]/'workflows/specs/cycles/raycaster-budget.json').read_text())
        for key in ('turn','walk'):
            limits=budget['segments'][key]['max_ticks_per_frame_by_symbol']
            # LTO can inline column_upload into main. Verify their COMBINED
            # cost is bounded, not just whichever ELF symbol survives.
            groups=budget['segments'][key]['max_ticks_per_frame_by_symbol_groups']
            self.assertTrue(any(set(group['symbols'])=={'main','column_upload'} and
                                group['max']<=300000 for group in groups))
            self.assertIn('cast_scene',limits)
            self.assertIn('cast_ray',limits)
            self.assertIn('irq_vdc',limits)
            self.assertNotIn('pce_memop',limits)
            self.assertGreaterEqual(budget['segments'][key]['min_attributed_pct'],96)

    def test_short_masked_tail_or_codegen_only(self):
        src=(ROOT/'src/main.c').read_text()
        self.assertIn('RAY_COLUMN_CHUNK_WORDS 8u',src)
        self.assertIn('RAY_COLUMN_TIA 0',src)
        self.assertIn('RAY_CANONICAL_WALL_KEY 1',src)
        self.assertIn('old_height[c]!=h',src)
        self.assertIn('for(uint8_t c=l;c<=r;++c)',src)
        self.assertIn('RAY_CANONICAL_WALL_KEY=0', (ROOT/'Makefile').read_text())
        self.assertIn('RAY_COLUMN_TIA=1', (ROOT/'Makefile').read_text())
        self.assertIn('ray_codegen_emit()',src)

    @staticmethod
    def sample(rate):
        segments=[]
        for name,frames,keys in column_benchmark.SCENARIO:
            moving=name in ('turn-right','walk','turn-left')
            segments.append({'segment':name,'emulator_frames':frames,'buttons':list(keys),
                 'dirty_views':6 if moving else 0,'vram_words':2000 if moving else 0,
                 'game_updates':24,'screenshot_colors':12})
        return {'scenario':segments,'totals':{'turning_views_per_second':rate}}

    def test_fps_comparison_rejects_regression(self):
        with self.assertRaisesRegex(ValueError,'regressed'):
            compare_scalar.compare(self.sample(6),self.sample(5))

    def test_fps_comparison_requires_identical_controller_schedule(self):
        a,b=self.sample(6),self.sample(7)
        b['scenario'][1]['buttons']=['left']
        with self.assertRaisesRegex(ValueError,'schedule'):
            compare_scalar.compare(a,b)

    def test_fps_comparison_rejects_blank_scene_or_stall(self):
        a,b=self.sample(6),self.sample(7)
        b['scenario'][3]['screenshot_colors']=2
        with self.assertRaisesRegex(ValueError,'blank'):
            compare_scalar.compare(a,b)
        b=self.sample(7);b['scenario'][3]['game_updates']=0
        with self.assertRaisesRegex(ValueError,'stalled'):
            compare_scalar.compare(a,b)

    def test_fps_comparison_reports_non_fixed_work(self):
        x=compare_scalar.compare(self.sample(6),self.sample(7))
        self.assertTrue(x['passed']);self.assertEqual(x['improvement_pct'],16.67)
        self.assertIn('NOT guaranteed identical',x['limitations'][0])

if __name__=='__main__':unittest.main()
