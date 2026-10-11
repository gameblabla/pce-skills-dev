"""VCS-inspired cell-crossing and empty-grid skip versus exact Q8 reference.

Gridline checks must be bit-exact: a one-step overshoot changes both the 32x32
texture phase and the wall-face flag. Test all directions near cell boundaries.
"""
from pathlib import Path
import importlib.util
import unittest

EXAMPLE=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
spec=importlib.util.spec_from_file_location('oracle',EXAMPLE/'tools/check_128_rays.py')
oracle=importlib.util.module_from_spec(spec)
# check_128_rays imports sibling generators
import sys
sys.path.insert(0,str(EXAMPLE/'tools'))
spec.loader.exec_module(oracle)


def fast_cast(c,wx,wy,angle):
    dx,dy=oracle.steps[angle][c]
    x,y=wx,wy
    cx,cy=x>>8,y>>8
    n=1
    while n<=32:
        if n<32:
            x2,y2=x+2*dx,y+2*dy
            if x>>8==x2>>8 and y>>8==y2>>8:
                x,y=x2,y2
                n+=2
                continue
        x+=dx;y+=dy
        nx,ny=x>>8,y>>8
        if nx==cx and ny==cy:
            n+=1
            continue
        m=oracle.mat(x,y)
        if m:
            px,py=x-dx,y-dy
            mx=px+((x-px)>>1);my=py+((y-py)>>1)
            if oracle.mat(mx,my):x,y=mx,my
            else:px,py=mx,my
            face=(px>>8)!=(x>>8)
            phase=(y if face else x)&255
            return (n,phase>>4,m|(128 if face else 0), ((y>>8)&255)*8+((x>>8)&255),phase)
        cx,cy=nx,ny
        n+=1
    return (32,0,1,255,0)


class RayGridCrossingTests(unittest.TestCase):
    def test_grid_skip_equivalent_over_multiple_wall_faces_and_boundaries(self):
        total=0
        for cy in range(1,7):
            for cx in range(1,7):
                if oracle.MAP[cy][cx]:
                    continue
                for fx,fy in ((1,1),(255,255),(128,128),(2,254),(254,2)):
                    wx,wy=(cx<<8)+fx,(cy<<8)+fy
                    for angle in range(16):
                        for ray in range(128):
                            self.assertEqual(oracle.cast(ray,wx,wy,angle),
                                             fast_cast(ray,wx,wy,angle),
                                             (cx,cy,fx,fy,angle,ray))
                            total+=1
        self.assertGreater(total,200000)

    def test_opt_in_only_and_robust_two_step_guard(self):
        text=(EXAMPLE/'src/main.c').read_text()
        self.assertIn('#define RAY_GRID_CROSSING 0',text)
        self.assertIn('#if RAY_GRID_CROSSING',text)
        self.assertIn('if(n<32u)',text)
        self.assertIn('(x^x2)',text)
        self.assertIn('(y^y2)',text)
        self.assertIn('cx=nx;cy=ny',text)
        self.assertIn('/* Conservative NES-style sparse',text)


if __name__=='__main__':unittest.main()
