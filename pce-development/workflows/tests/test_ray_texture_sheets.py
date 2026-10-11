"""Source-sheet reproducibility and dual-layer SGX budget boundaries."""
import sys,unittest,json
from pathlib import Path
from PIL import Image
PROJECT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
sys.path.insert(0,str(PROJECT/'tools'))
import gen_texture_sheet as pce
import sgx_texture_plan as sgx

class TextureSheetTests(unittest.TestCase):
    def test_sheets_stay_vendored_and_deterministic(self):
        self.assertEqual(Image.open(PROJECT/'assets/wolftextures16.png').size,(224,32))
        self.assertEqual(Image.open(PROJECT/'assets/wolftextures256.png').size,(224,32))
        header,palette,manifest=pce.generate()
        self.assertEqual((PROJECT/'src/sheet_pairs.h').read_text(),header)
        self.assertEqual((PROJECT/'src/sheet_palette.h').read_text(),palette)
        self.assertEqual((PROJECT/'assets/texture_manifest.json').read_text(),manifest)
        self.assertEqual(json.loads(manifest)['source_pce_unique_colours'],15)

    def test_16_colours_and_exact_paired_indices(self):
        pairs=pce.converted();self.assertEqual(len(pairs),14)
        for style in range(14):
            for u in range(16):
                self.assertEqual(len(pairs[style][u]),16)
                for v in range(16):
                    packed=pairs[style][u][v]
                    self.assertLess(packed>>4,16)
                    self.assertLess(packed&15,16)
                    self.assertEqual(packed&15,pairs[style][(u+1)&15][v]>>4)

    def test_near_wall_texture_preserves_original_32_by_32_art(self):
        # Two vertically adjacent original texels share one byte, without
        # throwing away every other source row as the far texture does.
        import re
        self.assertEqual((PROJECT/'src/hires_texels.h').read_text(),pce.generate_hires())
        atlas=Image.open(PROJECT/'assets/wolftextures16.png').convert('RGB')
        body=pce.generate_hires().split('ray_wall_hires[7][32][16] = {',1)[1].split('};',1)[0]
        packed=[int(s,16) for s in re.findall(r'0x([0-9a-f]{2})',body)]
        self.assertEqual(len(packed),7*32*16)
        for m in range(7):
            for u in range(32):
                for v in range(32):
                    b=packed[m*512+u*16+(v>>1)]
                    texel=(b&15) if (v&1) else (b>>4)
                    self.assertEqual(texel,pce.nearest(atlas.getpixel((m*32+u,v))))

    def test_subpixel_blend_matches_quantized_palette_midpoint(self):
        import re
        text=pce.generate()[1]
        body=text.split('ray_palette_blend_packed[128]={',1)[1].split('};',1)[0]
        packed=[int(s,16) for s in re.findall(r'0x([0-9a-f]{2})',body)]
        self.assertEqual(len(packed),128)
        quant=lambda rgb:tuple(round(c*7/255) for c in rgb)
        q=[quant(rgb) for rgb in pce.PALETTE]
        for a in range(16):
            for b in range(16):
                raw=packed[(a*16+b)>>1]
                mid=(raw&15) if b&1 else raw>>4
                avg=tuple((q[a][i]+q[b][i])/2 for i in range(3))
                correct=min(range(16),key=lambda k:sum((q[k][i]-avg[i])**2 for i in range(3)))
                self.assertEqual(mid,correct)
        native=(PROJECT/'src/bat_bitmap.h').read_text()
        self.assertIn('0xe0u',native) # three left source pixels
        self.assertIn('0x18u',native) # two midpoint pixels
        self.assertIn('0x07u',native) # three right source pixels

    def test_sgx_plan_validates_both_pixel_layers(self):
        header,report,preview=sgx.generate()
        self.assertEqual((PROJECT/'src/sgx_texture_planes.h').read_text(),header)
        self.assertEqual((PROJECT/'assets/sgx_dual_plan.json').read_text(),report)
        self.assertEqual(preview.tobytes(),Image.open(PROJECT/'assets/sgx_dual_preview.png').convert('RGB').tobytes())
        m=json.loads(report)
        self.assertFalse(m['runtime_verified'])
        self.assertEqual(m['source_unique_colours'],105)
        self.assertEqual(m['total_rom_plane_bytes'],7168)
        for material in m['per_material']:
            self.assertLessEqual(material['vdc_a_colors'],15)
            self.assertLessEqual(material['vdc_b_colors'],15)
            self.assertEqual(material['packed_pair_bytes_per_vdc'],512)

if __name__=='__main__':unittest.main()
