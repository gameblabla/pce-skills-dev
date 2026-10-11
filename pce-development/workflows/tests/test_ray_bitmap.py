"""Regression gates for PCE 512x224 BAT-backed bitmap raycasting."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest
from PIL import Image

PROJ=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
sp=importlib.util.spec_from_file_location('ray_bitmap', PROJ/'tools/check_bitmap.py')
bm=importlib.util.module_from_spec(sp);sp.loader.exec_module(bm)

class RayBitmapTests(unittest.TestCase):
    def test_renderer_is_paired_bat_bitmap_not_planar_tile_column(self):
        c=(PROJ/'src/main.c').read_text()
        h=(PROJ/'src/bat_bitmap.h').read_text()
        self.assertIn('bat_bitmap_setup(ray_sheet_palette)',c)
        self.assertIn('bat_bitmap_display()',c)
        self.assertIn('VDC_BG_SIZE_128_64',h)
        self.assertIn('512,224',h)
        self.assertIn('0xf200u',c)
        self.assertIn('uint8_t bitmap_pair(',c)
        self.assertIn('wall_pixel(',c)
        self.assertNotIn('pce_vdc_copy_to_vram(',c)
        self.assertNotIn('VDC_BG_SIZE_32_32',c)

    @staticmethod
    def sample_scene(path,cyan=False):
        im=Image.new('RGB',(560,242),'black')
        for y in range(22,222):
            for x in range(40,520):
                if y<87:
                    c=[(0,0,36),(0,0,72),(0,36,108)][(y-22)//22 if y<66 else 2]
                elif y<160:
                    c=[(108,72,36),(216,144,72),(36,36,36),(252,216,144),(72,72,72)][(x//9+y//9)%5]
                else:
                    c=[(72,36,0),(108,72,36),(36,36,36)][(x//12+y//12)%3]
                im.putpixel((x,y),c)
        if cyan:im.putpixel((100,198),(0,200,200))
        im.save(path)

    def test_multilayer_bitmap_capture_passes(self):
        with TemporaryDirectory() as t:
            file=Path(t)/'sample.png';self.sample_scene(file)
            self.assertTrue(bm.check(file)['passed'])

    def test_black_frame_fails(self):
        with TemporaryDirectory() as t:
            file=Path(t)/'black.png';Image.new('RGB',(560,242)).save(file)
            with self.assertRaises(ValueError):bm.check(file)

    def test_cyan_hole_fails(self):
        with TemporaryDirectory() as t:
            file=Path(t)/'hole.png';self.sample_scene(file,cyan=True)
            with self.assertRaisesRegex(ValueError,'cyan'):bm.check(file)

    def test_wrong_dimensions_fail(self):
        with TemporaryDirectory() as t:
            file=Path(t)/'small.png';Image.new('RGB',(256,224)).save(file)
            with self.assertRaisesRegex(ValueError,'560x242'):bm.check(file)

if __name__=='__main__':unittest.main()
