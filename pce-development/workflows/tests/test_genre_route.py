"""AI routing must choose genre-specific tools, not platformer P2TR by accident."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import offline

class GenreRouteTests(unittest.TestCase):
    def test_vn_project(self):
        self.assertEqual(offline.choose('Visual novel with mouth animation and static portraits'),'visual_novel')
        self.assertIn('visual-test',' '.join(offline.guidance('visual_novel')['instructions']))
    def test_shmup_without_trace_is_playable_recipe(self):
        self.assertEqual(offline.choose('I want a SHMUP scrolling shooter'),'shmup')
        self.assertEqual(offline.choose('SHMUP debugging and trace'),'shmup_trace')
    def test_raycaster_has_no_fake_playable_claim(self):
        self.assertEqual(offline.choose('Wolfenstein 3D raycaster'),'raycaster')
        self.assertIn('does not draw a playable game',' '.join(offline.guidance('raycaster')['instructions']).lower())
    def test_racing_trace_and_hybrid_distinct(self):
        self.assertEqual(offline.choose('racing with tracing'),'racing_trace')
        self.assertEqual(offline.choose('Contra style platformer plus racing'),'hybrid')
if __name__=='__main__':unittest.main()
