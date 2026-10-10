"""Negative tests for actual screenshot-only mouth-locality acceptance."""
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'pce'))
from vn_visual_check import check

class VNVisualTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        a=Image.new('RGB',(280,242),(18,40,68))
        a.save(self.path/'a.png');self.initial=a
    def write(self,x,y,n=43):
        b=self.initial.copy()
        for i in range(n):b.putpixel((x+i%16,y+i//16),(230,110,90))
        b.save(self.path/'b.png')
    def test_mouth_localized(self):
        self.write(110,135)
        self.assertEqual(check(self.path/'a.png',self.path/'b.png')['changed_pixels'],43)
    def test_change_outside_mouth_fails(self):
        self.write(50,50)
        with self.assertRaisesRegex(ValueError,'escaped mouth'):
            check(self.path/'a.png',self.path/'b.png')
    def test_no_change_fails(self):
        self.initial.save(self.path/'b.png')
        with self.assertRaisesRegex(ValueError,'identical'):
            check(self.path/'a.png',self.path/'b.png')
    def test_nearly_invisible_change_fails(self):
        self.write(110,135,1)
        with self.assertRaisesRegex(ValueError,'too subtle'):
            check(self.path/'a.png',self.path/'b.png')
if __name__=='__main__':unittest.main()
