"""Offline geometry and reproducibility checks for experimental BAT page selection."""
import sys
import random
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]/'examples'/'34-rendered-raycaster'
sys.path.insert(0,str(BASE/'tools'))
import gen_pageflip_tiled as tiled

class TiledPageFlipTests(unittest.TestCase):
    def test_no_visible_page_overlap(self):
        pages=[{(row<<7)+(page<<6)+col for row in range(32) for col in range(64)}
               for page in (0,1)]
        self.assertEqual((len(pages[0]),len(pages[1])),(2048,2048))
        self.assertFalse(pages[0].intersection(pages[1]))
        self.assertTrue(all(v<0x2000 for page in pages for v in page))
        self.assertLess(0x2000+256*16,0x3001)

    def test_glyph_palette_and_scroll_schedule(self):
        s=tiled.quant()
        self.assertIn('ray_tiled_palettes[16][2]',s)
        self.assertEqual(len(tiled.PAIRS),16)
        self.assertEqual(len(set(tiled.PAIRS)),16)
        asm=tiled.irq()
        self.assertIn('    eor #1',asm)
        self.assertIn('    stz ray_flip_pending',asm)
        self.assertIn('    cpx #31',asm)
        self.assertIn('    st2 #2',asm)
        self.assertIn('    st2 #0',asm)
        # RCR=0x41+7, then one skipped scanline every 7 physical lines.
        self.assertIn('    st1 #$48',asm)

    def test_rom_packed_pair_lookup_exactness(self):
        # Exhaust all palette/pixel-pair entries, and thousands of full tiles.
        # uint8_t scoring in the legacy renderer intentionally wraps modulo
        # 256; the accelerated result must preserve that for exact pictures.
        q=[[int(tiled.distance(c,b)<tiled.distance(c,a)) for c in range(16)]
           for a,b in tiled.PAIRS]
        errors=[[min(tiled.distance(c,a),tiled.distance(c,b)) for c in range(16)]
                for a,b in tiled.PAIRS]
        pair_error=[[errors[g][v>>4]+errors[g][v&15] for v in range(256)]
                    for g in range(16)]
        pair_mask=[[(q[g][v>>4]<<1)|q[g][v&15] for v in range(256)]
                   for g in range(16)]
        for g in range(16):
            for v in range(256):
                self.assertLess(pair_error[g][v],256)
                self.assertLess(pair_mask[g][v],4)
        rnd=random.Random(25601)
        best=[min(range(16),key=lambda g:errors[g][v>>4]+errors[g][v&15])
              for v in range(256)]
        for _ in range(8192):
            pairs=[rnd.randrange(256) for _ in range(4)]
            g0,g1=best[pairs[0]],best[pairs[-1]]
            legacy_colors=[c for v in pairs for c in (v>>4,v&15)]
            old0=sum(errors[g0][c] for c in legacy_colors)&255
            old1=sum(errors[g1][c] for c in legacy_colors)&255
            new0=sum(pair_error[g0][v] for v in pairs)&255
            new1=sum(pair_error[g1][v] for v in pairs)&255
            self.assertEqual((old0,old1),(new0,new1))
            pal=g1 if old1<old0 else g0
            old_pattern=0
            for c in legacy_colors:old_pattern=(old_pattern<<1)|q[pal][c]
            new_pattern=0
            for v in pairs:new_pattern=(new_pattern<<2)|pair_mask[pal][v]
            self.assertEqual(old_pattern,new_pattern)

    def test_generated_sources_and_no_full_bat_dma_copy(self):
        self.assertEqual((BASE/'src'/'pageflip_tiled_quant.h').read_text(),tiled.quant())
        self.assertEqual((BASE/'src'/'bat_pageflip_tiled_irq.S').read_text(),tiled.irq())
        source=(BASE/'src'/'pageflip_tiled.c').read_text()
        self.assertIn('while(ray_flip_pending)',source)
        self.assertIn('flip_next_group==64u',source)
        self.assertNotIn('pce_vdc_dma_start(',source)

if __name__=='__main__':unittest.main()
