"""Offline regression for pixel evidence, VDC pass accounting and comparisons."""
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PIL import Image, ImageDraw

TOOLS=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster/tools'
sys.path.insert(0,str(TOOLS))
import bitmap_stress as s
import bitmap_compare as c


class BitmapThroughputTests(unittest.TestCase):
    def samples(self,passes=10):
        return [{'segment':i,'buttons':list(b),'emulator_frames':frames,
                 'total_redraws':(i+1)*passes,'game_updates':(i+1)*40,
                 'bitmap':{'passed':True}}
                for i,(frames,b) in enumerate(s.STEPS)]

    def report(self,passes=10):
        samples=self.samples(passes)
        return {'result':'passed','format':'paired-bat-completed-pass-v1',
                'segments':samples,'totals':s.validate(samples)}

    def test_rejects_bogus_redraws_or_stale_screenshots(self):
        self.assertEqual(s.validate(self.samples())['completed_redraws'],60)
        cases=[(3,'total_redraws',0),(4,'game_updates',0),
               (1,'bitmap',{'passed':False}),(2,'segment',22)]
        for index,key,value in cases:
            samples=self.samples();samples[index][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):s.validate(samples)

    def test_comparison_demands_identical_input_and_more_complete_passes(self):
        base=self.report(2);fast=self.report(3)
        result=c.compare(base,fast)
        self.assertEqual(result['result'],'passed')
        self.assertEqual(result['completed_redraw_improvement_pct'],50)
        self.assertEqual(c.compare(fast,base)['result'],'regression')
        fast['segments'][1]['buttons']=['left']
        with self.assertRaisesRegex(ValueError,'scenarios differ'):c.compare(base,fast)
        fast=self.report(3);fast['result']='failed'
        with self.assertRaisesRegex(ValueError,'must pass'):c.compare(base,fast)

    def test_screen_checker_requires_real_wall_and_floor_without_forcing_bricks(self):
        with TemporaryDirectory() as td:
            path=Path(td)/'view.png'
            im=Image.new('RGB',(560,242),(0,0,7))
            draw=ImageDraw.Draw(im)
            draw.rectangle((24,22,536,85),fill=(10,20,70))
            draw.rectangle((24,50,536,85),fill=(18,30,90))
            draw.rectangle((24,86,536,171),fill=(100,100,95))
            draw.rectangle((24,92,265,144),fill=(135,135,125))
            draw.rectangle((24,172,536,223),fill=(110,77,30))
            draw.rectangle((24,185,536,205),fill=(150,115,60))
            im.save(path)
            self.assertTrue(s.check_bitmap_frame(path)['passed'])
            im=Image.new('RGB',(560,242),(0,0,45));im.save(path)
            with self.assertRaisesRegex(ValueError,'blank/partial'):s.check_bitmap_frame(path)
            im=Image.new('RGB',(560,242),(0,190,190));im.save(path)
            with self.assertRaises(ValueError):s.check_bitmap_frame(path)

if __name__=='__main__':unittest.main()
