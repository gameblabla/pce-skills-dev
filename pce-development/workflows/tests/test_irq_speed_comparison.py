"""Offline invariants for the 128x128 IRQ performance comparison."""
import sys
import unittest
from pathlib import Path

TOOLS=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster/tools'
sys.path.insert(0,str(TOOLS))
import compare_irq_speed


def bench(turn=2.0):
    return {'scenario': [{'segment':'turn','buttons':['right'],
                          'emulator_frames':180,'game_updates':160}],
            'totals':{'turning_views_per_second':turn,
                      'changed_views':10,'vram_words':10000}}


class IRQSpeedComparisonTests(unittest.TestCase):
    def test_reports_passes_not_full_screen_fps(self):
        result=compare_irq_speed.compare(bench(1.8),bench(2.0),
            {'matched':True,'differing_pixels':0,'pixel_count':135520})
        self.assertTrue(result['passed'])
        self.assertIn('Dirty-view commits are not full-screen FPS',result['limitations'])
        self.assertEqual(result['new_turning_dirty_views_per_second'],2.0)

    def test_rejects_regressions_and_changed_pixels(self):
        with self.assertRaisesRegex(ValueError,'regressed'):
            compare_irq_speed.compare(bench(2.0),bench(1.8),
                {'matched':True,'differing_pixels':0,'pixel_count':135520})
        with self.assertRaisesRegex(ValueError,'pixels changed'):
            compare_irq_speed.compare(bench(),bench(),
                {'matched':False,'differing_pixels':8,'pixel_count':135520})

    def test_rejects_different_video_scenarios(self):
        new=bench()
        new['scenario'][0]['emulator_frames']=240
        with self.assertRaisesRegex(ValueError,'not comparable'):
            compare_irq_speed.compare(bench(),new,
                {'matched':True,'differing_pixels':0,'pixel_count':135520})


if __name__=='__main__':unittest.main()
