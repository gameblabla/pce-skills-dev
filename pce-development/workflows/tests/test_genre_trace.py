"""Cross-genre G2TR v2 tests including failures seen in AI-produced games."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'pce'))
import genre_trace as tr


def sample(genre,**kw):
    return tr.decode(tr.encode_for_test(genre,**kw))


class GenreTraceTests(unittest.TestCase):
    def test_legacy_p2tr_layout_unchanged(self):
        import platformer_trace as old
        self.assertEqual(old.TRACE_BYTES,216)

    def test_fixed_wire_size(self):
        self.assertEqual(tr.FORMAT.size,64)
        for genre in tr.GENRES.values():
            self.assertEqual(sample(genre)['genre'],genre)

    def test_no_partial_record_chosen(self):
        complete=tr.encode_for_test('racing',frame=5,sequence=10)
        incomplete=tr.encode_for_test('racing',frame=6,sequence=11)
        self.assertEqual(tr.choose(complete+incomplete)['frame'],5)
        self.assertEqual(tr.choose(incomplete+complete)['frame'],5)
        with self.assertRaises(ValueError):tr.choose(incomplete+incomplete)

    def test_corrupt_bytes_rejected(self):
        with self.assertRaises(ValueError):tr.decode(b'P2TR'+bytes(60))
        with self.assertRaises(ValueError):tr.choose(bytes(120))
        with self.assertRaises(ValueError):tr.decode(bytes(65))

    def test_shmup_counters(self):
        valid=sample('shmup',state=(4,6,4,0))
        self.assertFalse(tr.validate([valid])['issues'])
        bad=sample('shmup',state=(65,-1,4,-2))
        codes={i['code'] for i in tr.validate([bad])['issues']}
        self.assertIn('sat_budget',codes)
        self.assertIn('negative_shmup_counter',codes)
        self.assertIn('shots_counter_reset',{i['code'] for i in tr.validate([valid,sample('shmup',frame=2,state=(2,2,3,0))])['issues']})

    def test_raycaster_columns_and_depth(self):
        good=sample('raycaster',state=(128,120,256,1200))
        self.assertFalse(tr.validate([good])['issues'])
        bad=sample('raycaster',state=(64,70,-5,1))
        codes={i['code'] for i in tr.validate([bad])['issues']}
        self.assertIn('ray_columns_invalid',codes)
        self.assertIn('ray_depth_invalid',codes)

    def test_racing_progress_and_screen_alignment(self):
        good=sample('racing',x=120,camera_x=12,screen_x=108,state=(0,300,100,4))
        self.assertFalse(tr.validate([good])['issues'])
        bad=sample('racing',frame=2,x=120,camera_x=20,screen_x=120,state=(0,200,-2,70))
        codes={i['code'] for i in tr.validate([good,bad])['issues']}
        for code in ('camera_x_mismatch','negative_speed','race_objects_invalid'):
            self.assertIn(code,codes)

    def test_visual_novel_mouth_dialogue(self):
        a=sample('visual_novel',state=(1,1,0,1))
        b=sample('visual_novel',frame=2,state=(1,1,1,1))
        self.assertFalse(tr.validate([a,b])['issues'])
        bad=sample('visual_novel',frame=3,state=(1,0,1,0))
        codes={i['code'] for i in tr.validate([a,b,bad])['issues']}
        self.assertIn('mouth_without_portrait',codes)
        self.assertIn('dialogue_regressed',codes)

    def test_scenario_validation(self):
        spec={'steps':[{'frames':2,'buttons':['right']},{'frames':1,'buttons':[]}],
              'require_genres':['shmup']}
        samples=[sample('shmup',frame=i,state=(1,2,i,0)) for i in range(3)]
        self.assertFalse(tr.validate(samples,spec)['issues'])
        broken=dict(spec,require_genres=['racing'])
        self.assertEqual(tr.validate(samples,broken)['issues'][0]['code'],'missing_genre')
        with self.assertRaises(ValueError):tr.validate(samples,dict(spec,steps=[{'frames':5,'buttons':['jump'] }]))
        with self.assertRaises(ValueError):tr.validate(samples,dict(spec,steps=[{'frames':5,'buttons':['right','right'] }]))
        self.assertEqual(tr.validate(samples[:1],spec)['issues'][0]['code'],'incomplete_trace')

    def test_instrumentation_probe_does_not_fake_visibility(self):
        s=sample('shmup',flags=2,state=(3,4,5,0))
        self.assertFalse(tr.validate([s])['issues'])
        self.assertFalse(s['flags'] & 1)

    def test_state_stuck_is_not_accepted(self):
        s=[sample('visual_novel',frame=i,state=(1,1,0,1)) for i in range(5)]
        spec={'steps':[{'frames':5,'buttons':[]}],
              'require_genres':['visual_novel'],
              'require_state_variation':{'visual_novel':[2]}}
        self.assertEqual(tr.validate(s,spec)['issues'][0]['code'],'state_not_changing')
        s[3]=sample('visual_novel',frame=3,state=(1,1,1,1))
        self.assertFalse(tr.validate(s,spec)['issues'])

    def test_camera_outlier(self):
        s=sample('platformer',x=52,camera_x=20,screen_x=100, state=(1,0,2,0))
        self.assertEqual(tr.validate([s])['issues'][0]['code'],'camera_x_mismatch')

if __name__=='__main__':unittest.main()
