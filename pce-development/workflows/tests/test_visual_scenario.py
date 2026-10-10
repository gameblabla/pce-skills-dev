"""Reject blank, fake and off-screen visual confirmations before emulator use."""
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'pce'))
import visual_scenario
class VisualAcceptanceTests(unittest.TestCase):
    def test_changed_pixels_inside_requested_region(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);a=Image.new('RGB',(256,224),(0,0,0));b=a.copy()
            ImageDraw.Draw(b).rectangle((100,120,130,160),fill=(200,20,20))
            a.save(p/'a.png');b.save(p/'b.png')
            r=visual_scenario.check_pngs(p/'a.png',p/'b.png',{
                'min_colors':2,'min_changed_pixels':300,
                'changed_region':[95,110,145,175],'min_region_changed_pixels':300})
            self.assertGreater(r['region_changed_pixels'],300)
    def test_no_visual_change_must_fail(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);im=Image.new('RGB',(256,224),(0,0,0));im.save(p/'a.png');im.save(p/'b.png')
            with self.assertRaisesRegex(ValueError,'visible colours'):
                visual_scenario.check_pngs(p/'a.png',p/'b.png',{'min_colors':5})
            with self.assertRaisesRegex(ValueError,'pixels changed'):
                visual_scenario.check_pngs(p/'a.png',p/'b.png',{'min_colors':1,'min_changed_pixels':1})
    def test_wrong_region_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);a=Image.new('RGB',(256,224),(0,0,0));b=a.copy();b.putpixel((1,1),(255,255,255))
            a.save(p/'a.png');b.save(p/'b.png')
            with self.assertRaisesRegex(ValueError,'inside the gameplay region'):
                visual_scenario.check_pngs(p/'a.png',p/'b.png',{'changed_region':[100,100,200,200],
                                                            'min_region_changed_pixels':1})
            with self.assertRaisesRegex(ValueError,'bounds'):
                visual_scenario.check_pngs(p/'a.png',p/'b.png',{'changed_region':[200,100,300,200]})
if __name__=='__main__':unittest.main()
