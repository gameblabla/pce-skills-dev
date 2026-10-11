"""Generated PCE-specific natural BYR schedule invariants; no emulator required."""
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
spec=importlib.util.spec_from_file_location('gen_sparse_irq',ROOT/'tools/gen_sparse_irq.py')
ray=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ray)


class NaturalIRQTests(unittest.TestCase):
    def test_emitted_assembly_matches_generator(self):
        self.assertEqual((ROOT/'src/bat_natural_irq.S').read_text(),ray.gen_natural())

    def test_all_logical_lines_present_and_page_switch_preserved(self):
        visited=[0]
        while visited[-1]<126:
            v=ray.natural_next(visited[-1])
            self.assertGreater(v,visited[-1])
            visited.append(v)
        self.assertEqual(len(visited)-1,68)
        self.assertEqual(ray.natural_next(126),128)
        self.assertEqual(visited.count(64),1)
        self.assertEqual(visited[visited.index(64)-1:visited.index(64)+2],[63,64,65])
        self.assertTrue(all(y in visited for y in range(60,69)))
        self.assertEqual(len([y for y in range(1,128) if y not in visited]),59)

    def test_natural_steps_cross_exactly_one_bat_tile(self):
        for y in range(2,127):
            if ray.natural_next(y)==y+2:
                duration=((y+1)*7+3)//4-(y*7+3)//4
                self.assertEqual(duration,2)
                self.assertEqual(ray.natural_offset(y)&7,5)
                following=((ray.natural_offset(y)+1+duration)>>3)&63
                self.assertEqual(following,ray.bat_row(y+1))
            elif y!=127:
                self.assertEqual(ray.natural_offset(y),ray.bat_row(y)*8-1)

    def test_byr_stays_in_page_on_emulated_seam(self):
        self.assertEqual(ray.natural_next(62),63)
        self.assertEqual(ray.natural_next(63),64)
        self.assertEqual(ray.natural_next(64),65)
        self.assertEqual(ray.natural_offset(63),63*8-1)
        self.assertEqual(ray.natural_offset(64),63*8-1)

if __name__=='__main__':unittest.main()
