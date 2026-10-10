"""Negative admission tests: local AI cannot pretend overflowing sprites render."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sat_budget import plan


def sprite(name,x=8,y=12,w=16,h=16,priority=0,vdc=0):
    return {'id':name,'x':x,'y':y,'w':w,'h':h,'priority':priority,'vdc':vdc}


class SatAdmissionTests(unittest.TestCase):
    def test_valid_baseline(self):
        d=plan({'sprites':[sprite('hero'),sprite('enemy',y=90)]})
        self.assertEqual(d['accepted_count'],2)
        self.assertEqual(d['dropped_count'],0)

    def test_scanline_overflow_is_rejected(self):
        d=plan({'sprites':[sprite(str(i)) for i in range(18)]})
        self.assertEqual(d['accepted_count'],16)
        self.assertEqual(sum(s['reason']=='scanline_16' for s in d['rejected']),2)

    def test_priority_keeps_hero_when_crowded(self):
        sprites=[sprite(f'enemy-{i}') for i in range(16)]+[sprite('hero',priority=255)]
        d=plan({'sprites':sprites})
        self.assertIn('hero',[s['id'] for s in d['accepted']])
        self.assertEqual(d['accepted'][0]['id'],'hero')

    def test_independent_supergrafx_limits(self):
        sprites=[sprite(str(i),vdc=i%2) for i in range(32)]
        d=plan({'vdcs':2,'sprites':sprites})
        self.assertEqual(d['accepted_count'],32)
        self.assertEqual(d['per_vdc'][0]['peak_scanline_sprites'],16)

    def test_sprite_height_and_width_validated(self):
        for w,h in [(8,8),(64,64),(32,8)]:
            with self.assertRaises(ValueError):plan({'sprites':[sprite('bad',w=w,h=h)]})

    def test_pixel_budget_and_offscreen(self):
        d=plan({'sprites':[sprite('hero',x=0),sprite('away',x=280),sprite('other',x=40)]})
        self.assertEqual(d['accepted_count'],2)
        self.assertEqual(d['rejected'][0]['reason'],'offscreen')

    def test_invalid_ids_or_vdc_rejected(self):
        with self.assertRaises(ValueError):plan({'sprites':[sprite('same'),sprite('same')]})
        with self.assertRaises(ValueError):plan({'sprites':[sprite('bad',vdc=1)]})

if __name__=='__main__': unittest.main()
