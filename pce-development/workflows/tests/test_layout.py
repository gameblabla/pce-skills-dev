import importlib.util
import re
from pathlib import Path
import unittest

BASE=Path(__file__).resolve().parents[2]

class BuiltRecipeSourceTests(unittest.TestCase):
    def test_hybrid_has_distinct_backgrounds(self):
        d=BASE/'examples/27-platformer-racer'
        program=(d/'src/main.c').read_text()
        video=(d/'src/demo_video.c').read_text()
        self.assertIn('demo_load_race_background();',program)
        self.assertIn('demo_video_init(256, VCE_PIXEL_CLOCK_5MHZ);',program)
        self.assertIn('pce_race_bat',video)
        self.assertNotIn('IO_PSG',program+video)
    def test_hybrid_telemetry_is_actual_game_state(self):
        text=(BASE/'examples/27-platformer-racer/src/main.c').read_text()
        self.assertIn('hybrid_race_progress_q8 += HYBRID_RACE_SPEED_Q8',text)
        self.assertIn('hybrid_race_lane_q8 = lane',text)
        self.assertIn('trace->scene = hybrid_scene ? 4 : PCE_TRACE_SCENE_PLAY',text)
    def test_no_dual_source_art_collision(self):
        text=(BASE/'examples/27-platformer-racer/src/main.c').read_text()
        self.assertIn('previous_feet <= top && proposed_feet >= top',text)
        self.assertIn('trace_surface(trace, i, &pce_demo_surfaces[i])',text)
    def test_rendered_art_generator_is_offline(self):
        text=(BASE/'examples/27-platformer-racer/tools/build_race_art.py').read_text()
        self.assertIn('planar_tile',text)
        self.assertIn('pce_race_bat',text)
        self.assertNotRegex(text,r'(urllib|requests|subprocess|imagegen|network)')

if __name__=='__main__':unittest.main()
