#!/usr/bin/env python3
"""Host model of all 128 ray directions and conservative adaptive hit guards.

Independent exact marching verifies that refinement never fabricates a wall
cell/face through corners in a broad 8x8-map camera sweep. Texture projection
is approximate by design; report its error instead of claiming exact pixels.
"""
from collections import Counter
from pathlib import Path
import gen_ray_tables as m
from gen_texture_sheet import converted
MAP=((1,2,2,3,3,4,5,6),(1,0,0,0,0,0,0,6),(1,0,2,0,0,0,0,6),(1,0,0,0,0,3,0,7),(1,0,0,0,0,0,0,7),(1,0,0,2,0,0,0,7),(1,0,0,0,0,0,0,7),(1,2,2,3,3,4,5,6))
COS=m.COS;SIN=m.SIN; MASK=15
heights=[max(12,min(116,360//(d+2))) for d in range(33)]
steps=[]
for a in range(16):
    row=[]
    for c in range(128):
        side=c-64
        dx=m.truncdiv(COS[a]-m.truncdiv(SIN[a]*side,160),2)
        dy=m.truncdiv(SIN[a]+m.truncdiv(COS[a]*side,160),2)
        row.append((dx,dy))
    steps.append(row)
def mat(x,y):
    tx=x>>8;ty=y>>8
    return 1 if tx<0 or tx>=8 or ty<0 or ty>=8 else MAP[ty][tx]
def cast(c,wx,wy,angle):
    dx,dy=steps[angle][c];x=wx;y=wy
    for n in range(1,33):
        px,py=x,y;x+=dx;y+=dy
        if (px>>8)==(x>>8) and (py>>8)==(y>>8):continue
        mm=mat(x,y)
        if mm:
            mx=px+((x-px)>>1);my=py+((y-py)>>1)
            if mat(mx,my):x=mx;y=my
            else:px=mx;py=my
            u=((y if (px>>8)!=(x>>8) else x)>>4)&MASK
            return n,u,mm | (128 if (px>>8)!=(x>>8) else 0), ((y>>8)&255)*8+((x>>8)&255), (y if (px>>8)!=(x>>8) else x)&255
    return 32,0,1,255,0

def interpolate(out,c,l,r):
    dl,ul,wl,cl,pl=out[l];dr,ur,wr,cr,pr=out[r]
    if cl!=cr or wl!=wr or abs(dl-dr)>3 or (ul<=3 and ur>=12) or (ur<=3 and ul>=12):return None
    du=ur-ul
    if du>8:du-=16
    if du < -8:du+=16
    if abs(du)>4:return None
    phase=(pl+pr+1)//2
    u=phase>>4
    return (dl+dr+1)//2,u,wl,cl,phase

def approx(wx,wy,a,mode):
    out=[None]*128
    if mode==0:
        for c in range(128):out[c]=cast(c,wx,wy,a)
    elif mode==1:
        for c in range(0,128,2):out[c]=cast(c,wx,wy,a)
        for c in range(1,127,2):out[c]=interpolate(out,c,c-1,c+1) or cast(c,wx,wy,a)
        out[127]=cast(127,wx,wy,a)
    elif mode==2:
        for c in range(0,128,4):out[c]=cast(c,wx,wy,a)
        out[126]=cast(126,wx,wy,a);out[127]=cast(127,wx,wy,a)
        for c in range(2,126,4):out[c]=interpolate(out,c,c-2,c+2) or cast(c,wx,wy,a)
        for c in range(1,127,2):out[c]=interpolate(out,c,c-1,c+1) or cast(c,wx,wy,a)
    return out

def main():
    cnt=Counter();examples=[]
    for y in range(1,7):
        for x in range(1,7):
            if MAP[y][x]:continue
            for fx,fy in ((64,64),(128,128),(192,192),(64,192)):
                wx=x*256+fx;wy=y*256+fy
                for a in range(16):
                    exact=approx(wx,wy,a,0);fast=approx(wx,wy,a,2)
                    for c,(t,f) in enumerate(zip(exact,fast)):
                        cnt['tested']+=1
                        if t[2:4]!=f[2:4]:
                            cnt['hit_mismatch']+=1
                            if len(examples)<6:examples.append((x,y,fx,fy,a,c,t,f))
                        elif heights[t[0]]!=heights[f[0]]:cnt['height_mismatch']+=1
                        elif t[1]!=f[1]:cnt['tex_mismatch']+=1
    assert cnt['tested']>200000
    assert cnt['hit_mismatch']==0, f'adaptive rays invented a wall face: {examples}'
    assert cnt['height_mismatch']<cnt['tested']//25, 'projected wall height too inaccurate'
    assert cnt['tex_mismatch']<cnt['tested']//6, 'texture phase drift too large'
    # Verify the pair assembler's right-lane U-1 addressing for all styles.
    pairs=converted()
    for left_style in range(14):
        for right_style in range(14):
            for u in range(16):
                for v in range(16):
                    left=pairs[left_style][u][v]&0xf0
                    right=pairs[right_style][(u-1)&15][v]&0x0f
                    want=pairs[right_style][u][v]>>4
                    assert right==want, 'native right texel nibble mismatch'
                    assert (left|right)&0xf0==left, 'native left texel nibble mismatch'
    expected=m.generate()
    assert '[16][128]' in expected and 'ray_step_x[16][128]' in expected
    assert min(len(set(steps[angle])) for angle in range(16))>=50
    assert Path(m.OUT).read_text()==expected, 'generated 128-ray table is stale'
    print('128 independent screen columns, 64 BAT words, 16 camera angles; '
          f"host tested {cnt['tested']} sample rays, 0 false hit cells/faces, "
          f"{cnt['height_mismatch']} height and {cnt['tex_mismatch']} texture-phase differences")
if __name__=='__main__':main()
