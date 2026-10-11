"""Validation contract for same-resolution contiguous BAT uploads."""
import importlib.util
from pathlib import Path
import unittest

TOOLS=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster/tools'
spec=importlib.util.spec_from_file_location('compare_vram_present',TOOLS/'compare_vram_present.py')
compare=importlib.util.module_from_spec(spec);spec.loader.exec_module(compare)

class VramPresentationTests(unittest.TestCase):
    @staticmethod
    def evidence(views=3,words=5000):
        return {'scenario':[{'segment':'turn-right','buttons':['right'],
                             'emulator_frames':180,'dirty_views':views,
                             'vram_words':words,'game_updates':170}],
                'totals':{'changed_views':views,'turning_views_per_second':views/3,
                          'vram_words':words}}
    @staticmethod
    def picture(differences=0):
        return {'matched':differences==0,'differing_pixels':differences,'pixel_count':135520}
    def test_same_pixels_and_views_pass(self):
        report=compare.compare(self.evidence(),self.evidence(),self.picture())
        self.assertTrue(report['passed'])
        self.assertEqual(report['resolution'],[128,128])
    def test_regression_rejected(self):
        with self.assertRaisesRegex(ValueError,'regresses'):
            compare.compare(self.evidence(3),self.evidence(2),self.picture())
    def test_pixel_discrepancy_rejected(self):
        with self.assertRaisesRegex(ValueError,'presentation changed'):
            compare.compare(self.evidence(),self.evidence(),self.picture(1))
    def test_input_scenario_mismatch_rejected(self):
        new=self.evidence();new['scenario'][0]['buttons']=['left']
        with self.assertRaisesRegex(ValueError,'camera scenarios'):
            compare.compare(self.evidence(),new,self.picture())

if __name__=='__main__':unittest.main()

class PacingComparisonTests(unittest.TestCase):
    @staticmethod
    def evidence(views=4):
        return {'scenario':[{'segment':'turn-right','buttons':['right'],
                             'emulator_frames':180,'dirty_views':views,
                             'vram_words':8000,'game_updates':170}],
                'totals':{'changed_views':views,'turning_views_per_second':views/3,
                          'vram_words':8000}}
    def test_equal_image_faster_pass_accepted(self):
        from importlib import util
        p=TOOLS/'compare_vram_pacing.py';spec=util.spec_from_file_location('compare_vram_pacing',p)
        m=util.module_from_spec(spec);spec.loader.exec_module(m)
        a=m.compare(self.evidence(3),self.evidence(4),{'matched':True,
                    'differing_pixels':0,'pixel_count':135520})
        self.assertTrue(a['passed'])
    def test_different_images_rejected(self):
        from importlib import util
        p=TOOLS/'compare_vram_pacing.py';spec=util.spec_from_file_location('compare_vram_pacing',p)
        m=util.module_from_spec(spec);spec.loader.exec_module(m)
        with self.assertRaisesRegex(ValueError,'exact stationary image'):
            m.compare(self.evidence(),self.evidence(),{'matched':False,'differing_pixels':1})
