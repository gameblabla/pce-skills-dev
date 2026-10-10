"""Host-side oracle for the higher-detail paired-BAT raycaster.

Exercises 64 actual rays against the 8x8 map at many camera positions.
The interpolation gate must never blend distinct hit cells or wall faces,
including at a texture U wrap (a frequent source of striped/corner artifacts).
"""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]/'examples/34-rendered-raycaster'
spec=importlib.util.spec_from_file_location('rays',ROOT/'tools/gen_ray_tables.py')
rays=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rays)

MAP=((1,2,2,3,3,4,5,6),
     (1,0,0,0,0,0,0,6),
     (1,0,2,0,0,0,0,6),
     (1,0,0,0,0,3,0,7),
     (1,0,0,0,0,0,0,7),
     (1,0,0,2,0,0,0,7),
     (1,0,0,0,0,0,0,7),
     (1,2,2,3,3,4,5,6))


def material(x,y):
    x,y=x//256,y//256
    return MAP[y][x] if 0<=x<8 and 0<=y<8 else 1


def exact_cast(angle,column,x,y):
    side=column-32
    dx=rays.truncdiv(rays.COS[angle]-rays.truncdiv(rays.SIN[angle]*side,80),2)
    dy=rays.truncdiv(rays.SIN[angle]+rays.truncdiv(rays.COS[angle]*side,80),2)
    for step in range(1,33):
        px,py=x,y
        x+=dx;y+=dy
        if px//256==x//256 and py//256==y//256:
            continue
        m=material(x,y)
        if not m:
            continue
        mx=px+(x-px)//2;my=py+(y-py)//2
        if material(mx,my):x,y=mx,my
        else:px,py=mx,my
        xface=px//256!=x//256
        return (step, ((y if xface else x)>>4)&15, m|(0x80 if xface else 0),
                (x//256,y//256))
    return (32,0,1,(-1,-1))


def can_interpolate(left,right):
    ld,lu,lface,lcell=left
    rd,ru,rface,rcell=right
    if lcell!=rcell or lface!=rface or abs(ld-rd)>3:
        return False
    if (lu<=3 and ru>=12) or (ru<=3 and lu>=12):
        return False
    du=ru-lu
    if du>8:du-=16
    if du< -8:du+=16
    return abs(du)<=4


class RayAdaptiveTests(unittest.TestCase):
    def test_one_vdc_bat_word_per_ray_and_bounded_chunks(self):
        text=(ROOT/'src/main.c').read_text()
        self.assertIn('depth[64]',text)
        self.assertIn('column_upload(c,first,last,c,u)',text)
        self.assertIn('RAY_COLUMNS_PER_UPDATE 16u',text)
        self.assertIn('RAY_COLUMN_CHUNK_WORDS 8u',text)
        self.assertIn('ray_hit_cell[c-1]!=ray_hit_cell[c+1]',text)
        self.assertIn('ul<=3u && ur>=12u',text)
        self.assertNotIn('column_upload((uint8_t)(c<<1)',text)

    def test_interpolation_is_safe_on_sampled_map_corners(self):
        examined=0;interpolated=0;corners=0
        for angle in range(16):
            for tx in range(1,7):
                for ty in range(1,7):
                    if MAP[ty][tx]:continue
                    for ox,oy in ((64,64),(128,128),(192,192),(64,192),(192,64)):
                        x=tx*256+ox;y=ty*256+oy
                        casts=[exact_cast(angle,c,x,y) for c in range(64)]
                        for c in range(1,63,2):
                            examined+=1
                            left,right=casts[c-1],casts[c+1]
                            if not can_interpolate(left,right):
                                if left[3]!=right[3] or left[2]!=right[2]:
                                    corners+=1
                                continue
                            actual=casts[c]
                            interpolated+=1
                            self.assertEqual((left[2],left[3]),(actual[2],actual[3]),
                                f'wall corner swallowed at {angle=} {x=} {y=} {c=}')
                            self.assertLessEqual(abs(actual[0]-(left[0]+right[0]+1)//2),1)
        self.assertGreater(examined,10000)
        self.assertGreater(interpolated,examined//3)
        self.assertGreater(corners,100)

if __name__=='__main__': unittest.main()
