"""VRAM layout and paced upload validation for AI-generated projects."""
import importlib.util
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('vram_budget',ROOT/'vram_budget.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def base(**k):
    d={'system':'pce','max_frames':3,'raster_irqs':True,
       'max_chunk_bytes':16,'bytes_per_frame':32,
       'regions':[{'id':'bat','start_word':0,'words':2048,'visibility':'back'}],
       'uploads':[{'id':'rows','region':'bat','bytes':80,'deadline_frame':2}]}
    d.update(k);return d

class VramPlannerTests(unittest.TestCase):
    def test_bounded_chunk_and_budget(self):
        result=v.plan(base())
        self.assertTrue(result['ok'])
        self.assertEqual(result['scheduled_bytes'],80)
        self.assertEqual([t['bytes'] for t in result['timeline']],[32,32,16])
        self.assertTrue(all(x['bytes']<=16 and x['bytes']%2==0
                 for frame in result['timeline'] for x in frame['chunks']))
        self.assertEqual(result['timeline'][0]['chunks'][0]['start_word'],0)
        self.assertEqual(result['timeline'][1]['chunks'][0]['start_word'],16)

    def test_vram_overlap_rejected_same_vdc(self):
        d=base(uploads=[],regions=[{'id':'a','start_word':0,'words':2048},
                                   {'id':'b','start_word':2047,'words':10}])
        with self.assertRaisesRegex(ValueError,'overlap'):v.plan(d)

    def test_vram_overlap_permitted_two_vdcs(self):
        d=base(system='supergrafx',uploads=[],regions=[
            {'id':'a','start_word':0,'words':2048,'vdc':0},
            {'id':'b','start_word':0,'words':2048,'vdc':1}])
        self.assertTrue(v.plan(d)['ok'])

    def test_pce_rejects_second_vdc(self):
        d=base(regions=[{'id':'bat','start_word':0,'words':32,'vdc':1}])
        with self.assertRaisesRegex(ValueError,'vdc'):v.plan(d)

    def test_unschedulable_deadline_detected(self):
        d=base(uploads=[{'id':'rows','region':'bat','bytes':80,'deadline_frame':0}])
        result=v.plan(d)
        self.assertFalse(result['ok']);self.assertIn('rows',result['late_uploads'])

    def test_incomplete_upload_detected(self):
        d=base(uploads=[{'id':'rows','region':'bat','bytes':128,'deadline_frame':2}])
        result=v.plan(d)
        self.assertFalse(result['ok']);self.assertEqual(result['incomplete'][0]['remaining_bytes'],32)

    def test_visible_vram_requires_explicit_vblank_contract(self):
        d=base(regions=[{'id':'bat','start_word':0,'words':2048,'visibility':'front'}])
        with self.assertRaisesRegex(ValueError,'vblank_only'):v.plan(d)
        d['uploads'][0]['vblank_only']=True
        self.assertTrue(v.plan(d)['ok'])

    def test_explicit_progressive_visible_bat_upload(self):
        d=base(regions=[{'id':'bat','start_word':0,'words':8192,'visibility':'front'}])
        d['uploads'][0]['progressive_visible']=True
        r=v.plan(d)
        self.assertTrue(r['ok'])
        self.assertTrue(r['contains_progressive_visible_writes'])
        self.assertTrue(all(x['bytes']<=16 and x['progressive_visible'] and not x['vblank_only']
                            for tick in r['timeline'] for x in tick['chunks']))
        d['uploads'][0]['vblank_only']=True
        with self.assertRaisesRegex(ValueError,'contradicts'):v.plan(d)
        d['uploads'][0].pop('vblank_only')
        d['raster_irqs']=False
        with self.assertRaisesRegex(ValueError,'raster_irqs'):v.plan(d)
        d['raster_irqs']=True
        d['max_chunk_bytes']=32
        with self.assertRaisesRegex(ValueError,'16'):v.plan(d)
        d['max_chunk_bytes']=16
        d['uploads'][0]['progressive_visible']='true'
        with self.assertRaisesRegex(ValueError,'boolean'):v.plan(d)
        d['uploads'][0]['progressive_visible']=True
        d['regions'][0]['visibility']='back'
        with self.assertRaisesRegex(ValueError,'front BAT'):v.plan(d)

    def test_no_long_block_moves_under_raster(self):
        with self.assertRaisesRegex(ValueError,'16'):v.plan(base(max_chunk_bytes=64))

    def test_large_tia_allowed_only_with_explicit_vblank(self):
        example=json.loads((ROOT/'specs/raycaster-tia-vblank.json').read_text())
        p=v.plan(example)
        self.assertTrue(p['ok'])
        self.assertEqual(p['scheduled_bytes'],1024)
        self.assertEqual(len(p['timeline'][0]['chunks']),8)
        self.assertTrue(all(x['bytes']==128 and x['vblank_only']
                            for x in p['timeline'][0]['chunks']))
        # The two BAT halves have interleaved physical addresses, not 128
        # consecutive words. Cross the y=64 boundary correctly.
        self.assertEqual([x['start_word'] for x in p['timeline'][0]['chunks']][3:5],
                         [8064,64])
        example['uploads'][0]['vblank_only']=False
        with self.assertRaisesRegex(ValueError,'visible VRAM'):
            v.plan(example)
        example['uploads'][0]['vblank_only']=True
        example['vblank_max_chunk_bytes']=127
        with self.assertRaisesRegex(ValueError,'even'):v.plan(example)

    def test_bad_sizes_and_bounds(self):
        for d in [base(bytes_per_frame=3),base(max_chunk_bytes=7),
                  base(regions=[{'id':'bat','start_word':32760,'words':16}]),
                  base(uploads=[{'id':'rows','region':'bat','bytes':81}]),
                  base(uploads=[{'id':'rows','region':'bat','offset_words':2047,'bytes':80}])]:
            with self.subTest(d=d),self.assertRaises(ValueError):v.plan(d)

    def test_duplicate_target_upload_rejected(self):
        d=base(uploads=[{'id':'a','region':'bat','bytes':48},
                        {'id':'b','region':'bat','bytes':48,'offset_words':12}])
        with self.assertRaisesRegex(ValueError,'overlaps upload'):v.plan(d)

    def test_priority_deadline_and_range(self):
        d=base(uploads=[{'id':'later','region':'bat','bytes':32,'offset_words':128,'deadline_frame':2},
                        {'id':'first','region':'bat','bytes':32,'deadline_frame':0}])
        r=v.plan(d)
        self.assertTrue(r['ok']);self.assertEqual(r['timeline'][0]['chunks'][0]['id'],'first')

    def test_real_scenario(self):
        fixture=json.loads((ROOT/'specs/vram-streaming.json').read_text())
        r=v.plan(fixture)
        self.assertTrue(r['ok'])
        self.assertLessEqual(max(t['bytes'] for t in r['timeline']),fixture['bytes_per_frame'])
        self.assertEqual(r['scheduled_bytes'],96+192+256+64)

if __name__=='__main__':unittest.main()
