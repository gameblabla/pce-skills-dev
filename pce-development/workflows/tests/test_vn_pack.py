"""Image constraints and memory allocation tests; no compiler/network needed."""
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'pce'))
import vn_pack

class VNPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        vn_pack.demo(self.root)
    def test_pack_and_preview(self):
        o=self.root/'out'
        manifest=vn_pack.pack(self.root/'background.png',self.root/'mouth_closed.png',self.root/'mouth_open.png',o)
        self.assertLess(manifest['background_unique_tiles'],896)
        self.assertEqual(manifest['mouth_changed_pixels'],43)
        self.assertEqual(manifest['background_palette_count'],1)
        self.assertLess(manifest['vram_words']['background_patterns'][1],0x6000)
        self.assertEqual(manifest['vram_words']['sprite_patterns'][0],0x6000)
        self.assertIn('VN_BG_PALETTES 1',(o/'vn_assets.h').read_text())
        self.assertNotEqual((o/'preview_open.png').read_bytes(),(o/'preview_closed.png').read_bytes())
    def test_wrong_background_dimensions_rejected(self):
        Image.new('RGB',(255,224)).save(self.root/'bad.png')
        with self.assertRaisesRegex(ValueError,'exactly 256x224'):
            vn_pack.pack(self.root/'bad.png',self.root/'mouth_closed.png',self.root/'mouth_open.png',self.root/'out')
    def test_wrong_sprite_dimensions_rejected(self):
        Image.new('RGBA',(16,17)).save(self.root/'bad.png')
        with self.assertRaisesRegex(ValueError,'exactly 16x16'):
            vn_pack.pack(self.root/'background.png',self.root/'bad.png',self.root/'mouth_open.png',self.root/'out')
    def test_excess_sprite_palette_rejected(self):
        image=Image.new('RGBA',(16,16),(0,0,0,0))
        for x in range(16):image.putpixel((x,0),(x*15,0,0,255))
        image.save(self.root/'bad.png')
        with self.assertRaisesRegex(ValueError,'>15 distinct'):
            vn_pack.pack(self.root/'background.png',self.root/'bad.png',self.root/'mouth_open.png',self.root/'out')
    def test_pixel_plane_encoding(self):
        px=[[0]*8 for _ in range(8)];px[0][0]=15
        data=vn_pack.plane(px,8,8)
        self.assertEqual(len(data),32)
        self.assertEqual([data[i] for i in (0,1,16,17)],[128]*4)
        sprite=[[0]*16 for _ in range(16)];sprite[0][15]=15
        data=vn_pack.plane(sprite,16,16)
        self.assertEqual(len(data),128)
        self.assertEqual([data[i] for i in (1,33,65,97)],[1]*4)
if __name__=='__main__':unittest.main()
