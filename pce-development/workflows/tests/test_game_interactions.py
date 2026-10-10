"""G2TR evidence tests for real game-state transitions, not mere ROM startup."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'pce'))
import genre_trace as g


def record(genre,frame,state,flags=3,buttons=0,x=3.5,y=3.5):
    return g.decode(g.encode_for_test(genre,frame=frame,state=state,flags=flags,
                                      buttons=buttons,x=x,y=y,screen_x=x,screen_y=y))


def test_spec(genre,event,**extra):
    return {'steps':[{'frames':2,'buttons':[]}], 'require_genres':[genre],
            'require_events':[event],**extra}


class GameInteractionTests(unittest.TestCase):
    def test_shmup_hit_requires_real_counter_change_and_collision(self):
        s=[record('shmup',1,(1,3,1,0)),record('shmup',2,(0,2,1,0),7)]
        self.assertFalse(g.validate(s,test_spec('shmup','shmup_enemy_hit'))['issues'])
        bad=[s[0],record('shmup',2,(0,2,1,0))]
        codes={i['code'] for i in g.validate(bad,test_spec('shmup','shmup_enemy_hit'))['issues']}
        self.assertIn('enemy_disappeared_without_hit',codes)
        self.assertIn('required_event_missing',codes)

    def test_damage_requires_collision(self):
        s=[record('shmup',1,(0,3,1,0)),record('shmup',2,(0,3,1,1),7)]
        self.assertFalse(g.validate(s,test_spec('shmup','shmup_player_damage'))['issues'])
        broken=[s[0],record('shmup',2,(0,3,1,1))]
        codes={i['code'] for i in g.validate(broken,test_spec('shmup','shmup_player_damage'))['issues']}
        self.assertIn('damage_without_collision',codes)

    def test_racer_checkpoint_and_lap_must_be_real(self):
        a=record('racing',1,(0,63*256,3*256,3))
        b=record('racing',2,(0,65*256,3*256,3),flags=11)
        c=record('racing',3,(0,257*256,3*256,3),flags=11)
        spec=test_spec('racing','racing_checkpoint')
        spec['require_events']=['racing_checkpoint','racing_lap']
        self.assertFalse(g.validate([a,b,c],spec)['issues'])
        bad=[a,record('racing',2,(0,65*256,3*256,3))]
        codes={i['code'] for i in g.validate(bad,test_spec('racing','racing_checkpoint'))['issues']}
        self.assertIn('checkpoint_not_published',codes)
        self.assertIn('required_event_missing',codes)

    def test_spurious_checkpoint_fails(self):
        a=record('racing',1,(0,10*256,3*256,3))
        b=record('racing',2,(0,13*256,3*256,3),flags=11)
        self.assertIn('spurious_checkpoint',
                      [i['code'] for i in g.validate([a,b],{'steps':[{'frames':2,'buttons':[]}]})['issues']])

    def test_raycaster_map_entry_detected(self):
        world=['#####','#...#','#.#.#','#...#','#####']
        a=record('raycaster',1,(32,32,64,128),x=1.5,y=1.5)
        b=record('raycaster',2,(32,32,64,128),x=2.5,y=2.5)
        spec=test_spec('raycaster','ray_wall_blocked',world_map=world)
        codes={i['code'] for i in g.validate([a,b],spec)['issues']}
        self.assertIn('entered_solid_wall',codes)
        self.assertIn('required_event_missing',codes)

    def test_short_emulator_sampling_gap_supported(self):
        s=[record('shmup',39,(1,3,1,0)),record('shmup',41,(0,2,1,0),flags=7)]
        spec={'steps':[{'frames':1,'buttons':[]}] ,'require_events':['shmup_enemy_hit']}
        self.assertFalse(g.validate(s,spec)['issues'])
        s[1]['frame']=44
        self.assertIn('required_event_missing',[i['code'] for i in g.validate(s,spec)['issues']])

    def test_unknown_required_event_rejected(self):
        with self.assertRaises(ValueError):g.validate([],{'steps':[{'frames':1,'buttons':[]}], 'require_events':['fake_win']})

    def test_solid_map_schema_rejected(self):
        for world in [[],['##','#'],['###','??#']]:
            with self.assertRaises(ValueError):g.validate([],{'steps':[{'frames':1,'buttons':[]}],'world_map':world})

if __name__=='__main__': unittest.main()
