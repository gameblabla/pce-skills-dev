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
        self.assertIn('demo_video_init(256,VCE_PIXEL_CLOCK_5MHZ);',program)
        self.assertIn('demo_restore_platform_background();',program)
        self.assertEqual(program.count('demo_video_init('),1)
        self.assertIn('pce_vdc_poke(VDC_REG_VRAM_DATA,sprite.attr)',video)
        self.assertIn('pce_race_bat',video)
        self.assertNotIn('IO_PSG',program+video)
    def test_hybrid_telemetry_is_actual_game_state(self):
        text=(BASE/'examples/27-platformer-racer/src/main.c').read_text()
        self.assertIn('hybrid_race_progress_px+=(HYBRID_RACE_SPEED_Q8/256)',text)
        self.assertIn('hybrid_race_lane_px=lane',text)
        self.assertIn('p4_publish(frame,hybrid_scene',text)
    def test_no_dual_source_art_collision(self):
        text=(BASE/'examples/27-platformer-racer/src/main.c').read_text()
        physics=(BASE/'examples/27-platformer-racer/src/platformer_q4.h').read_text()
        self.assertIn('old_feet<=top && new_feet>=top',physics)
        self.assertIn('p4_overlaps(p,&pce_demo_surfaces[i])',physics)
        self.assertIn('p4_tick(&player,pad,&events)',text)
    def test_rendered_art_generator_is_offline(self):
        text=(BASE/'examples/27-platformer-racer/tools/build_race_art.py').read_text()
        self.assertIn('planar_tile',text)
        self.assertIn('pce_race_bat',text)
        self.assertNotRegex(text,r'(urllib|requests|subprocess|imagegen|network)')

if __name__=='__main__':unittest.main()
