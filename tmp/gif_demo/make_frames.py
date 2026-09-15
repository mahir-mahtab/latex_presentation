import numpy as np
from PIL import Image, ImageDraw

W, H = 900, 500
SCALE = 1  # supersample factor could be added later

# palette (match CLAUDE.md)
NAVY   = (14, 35, 122)
STEEL  = (77, 111, 173)
SKY    = (93, 173, 245)
TEAL   = (63, 140, 138)
SLATE  = (91, 100, 117)
PAPER  = (251, 250, 247)
INK    = (28, 34, 51)
WHITE  = (255, 255, 255)

N_FRAMES = 24

# two simple 8x8 masks to morph between (not real MNIST, just a clean shape demo)
def mask_cross():
    m = np.zeros((8,8))
    m[3:5,:] = 1
    m[:,3:5] = 1
    return m

def mask_diamond():
    m = np.zeros((8,8))
    for y in range(8):
        for x in range(8):
            if abs(x-3.5)+abs(y-3.5) <= 3.2:
                m[y,x] = 1
    return m

A = mask_cross()
B = mask_diamond()

def lerp(a,b,t):
    return a*(1-t)+b*t

def ease(t):
    # smoothstep for nicer easing at the endpoints
    return t*t*(3-2*t)

frames = []
for i in range(N_FRAMES):
    t_raw = i/(N_FRAMES-1)
    # ping-pong: go 0->1 then back 1->0 within the loop for a seamless GIF
    t_raw = t_raw*2
    if t_raw > 1: t_raw = 2 - t_raw
    t = ease(t_raw)

    img = Image.new("RGB", (W,H), PAPER)
    d = ImageDraw.Draw(img)

    # ---------------- left: latent-space mini panel ----------------
    px0, py0, px1, py1 = 40, 60, 430, 440
    d.rectangle([px0,py0,px1,py1], outline=None, fill=WHITE)
    # faint grid
    for gx in range(px0, px1, 24):
        d.line([(gx,py0),(gx,py1)], fill=(230,230,225), width=1)
    for gy in range(py0, py1, 24):
        d.line([(px0,gy),(px1,gy)], fill=(230,230,225), width=1)
    d.rectangle([px0,py0,px1,py1], outline=SLATE, width=2)

    cx, cy = (px0+px1)//2, (py0+py1)//2
    d.line([(px0,cy),(px1,cy)], fill=(190,190,185), width=1)
    d.line([(cx,py0),(cx,py1)], fill=(190,190,185), width=1)

    # two clusters
    za = (px0+80, py0+90)   # "A" cluster centre  (top-left-ish)
    zb = (px1-90, py1-70)   # "B" cluster centre  (bottom-right-ish)
    rng = np.random.RandomState(4242)
    for (cx0,cy0,col) in [(za,None,NAVY),(zb,None,TEAL)]:
        pass
    def cloud(cxcy, col, n=26, spread=26):
        cxx,cyy = cxcy
        rs = np.random.RandomState(hash(col) % 5000)
        for _ in range(n):
            dx = rs.normal(0, spread); dy = rs.normal(0, spread)
            d.ellipse([cxx+dx-2, cyy+dy-2, cxx+dx+2, cyy+dy+2], fill=col)
    cloud(za, NAVY)
    cloud(zb, TEAL)

    # dashed path between cluster centres
    steps = 22
    for s in range(steps):
        if s % 2 == 0:
            f0 = s/steps; f1 = (s+0.6)/steps
            x0 = za[0] + (zb[0]-za[0])*f0; y0 = za[1] + (zb[1]-za[1])*f0
            x1 = za[0] + (zb[0]-za[0])*f1; y1 = za[1] + (zb[1]-za[1])*f1
            d.line([(x0,y0),(x1,y1)], fill=SLATE, width=2)

    # the moving point z(t)
    mx = za[0] + (zb[0]-za[0])*t
    my = za[1] + (zb[1]-za[1])*t
    d.ellipse([mx-7,my-7,mx+7,my+7], fill=WHITE, outline=NAVY, width=3)

    d.text((px0, py1+8), "latent space  (z-walk from A to B)", fill=SLATE)

    # ---------------- right: decoded output box ----------------
    bx0, by0, bx1, by1 = 520, 90, 860, 410
    d.rectangle([bx0,by0,bx1,by1], outline=SLATE, width=2, fill=WHITE)

    cell = (bx1-bx0-16)/8
    ox, oy = bx0+8, by0+8
    M = lerp(A,B,t)
    for gy in range(8):
        for gx in range(8):
            v = M[gy,gx]
            if v > 0.02:
                shade = tuple(int(WHITE[k] - v*(WHITE[k]-INK[k])) for k in range(3))
                x0 = ox+gx*cell; y0 = oy+gy*cell
                d.rectangle([x0,y0,x0+cell,y0+cell], fill=shade)

    d.text((bx0, by1+8), "decoded  p_theta(x | z(t))", fill=SLATE)

    # arrow from moving point toward decode box (visual link)
    d.line([(mx+10,my),(bx0-14,(by0+by1)//2)], fill=SLATE, width=1)
    d.polygon([(bx0-14,(by0+by1)//2-5),(bx0-14,(by0+by1)//2+5),(bx0-4,(by0+by1)//2)], fill=SLATE)

    # title
    d.text((40,20), "Walking through latent space", fill=NAVY)

    frames.append(img)

import os
os.makedirs("/d/code/latex_presentation/tmp/gif_demo/frames", exist_ok=True)
for i,f in enumerate(frames,1):
    f.save(f"/d/code/latex_presentation/tmp/gif_demo/frames/frame_{i:02d}.png")

frames[0].save("/d/code/latex_presentation/tmp/gif_demo/interpolation_demo.gif",
               save_all=True, append_images=frames[1:], duration=90, loop=0)
print("wrote", len(frames), "frames + gif")
