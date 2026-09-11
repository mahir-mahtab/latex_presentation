"""Procedurally generate the raster 'photos' used in Part 1.

Outputs (part1/img/):
  photo_original.jpg   - high-quality landscape photo (quality 95)
  photo_compressed.jpg - same photo, heavily JPEG-compressed (looks almost identical)
  gallery.png          - phone gallery grid of many small photos
Run:  python gen_images.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent / "img"
OUT.mkdir(exist_ok=True)


def lerp(a, b, t):
    return a + (b - a) * t


def noise1d(n, rng, octaves=6, base=3):
    out, amp, tot = np.zeros(n), 1.0, 0.0
    for o in range(octaves):
        k = base * 2 ** o
        pts = rng.uniform(-1, 1, k + 2)
        xs = np.linspace(0, k, n)
        i = np.floor(xs).astype(int).clip(0, k)
        f = xs - i
        f = f * f * (3 - 2 * f)
        out += amp * (pts[i] * (1 - f) + pts[i + 1] * f)
        tot += amp
        amp *= 0.5
    return out / tot


def noise2d(h, w, rng, octaves=5, base=3, stretch=1.0):
    out, amp, tot = np.zeros((h, w), np.float32), 1.0, 0.0
    for o in range(octaves):
        k = base * 2 ** o
        g = rng.uniform(0, 1, (k + 1, int(k * w / h / stretch) + 2)).astype(np.float32)
        im = Image.fromarray(g, mode="F").resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(im, np.float32)
        tot += amp
        amp *= 0.5
    return out / tot


def landscape(w, h, seed, p):
    rng = np.random.default_rng(seed)
    H = p["horizon"] * h
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    top, bot = np.array(p["top"], np.float32), np.array(p["bottom"], np.float32)

    # sky gradient
    t = np.clip(yy / H, 0, 1)[..., None] ** p.get("skypow", 1.0)
    img = lerp(top, bot, t)

    # sun / moon with glow
    sx, sy = p["sun"][0] * w, p["sun"][1] * h
    d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2) / h
    sc = np.array(p["suncol"], np.float32)
    glow = np.exp(-(d / p.get("glow", 0.18)) ** 2)[..., None]
    img = lerp(img, sc, glow * p.get("glowamt", 0.55))
    disk = np.clip((p["sunr"] - d) / 0.004, 0, 1)[..., None]
    img = lerp(img, sc, disk)

    # stars
    if p.get("stars"):
        m = (rng.random((h, w)) < 0.0012) & (yy < H * 0.75)
        img[m] = lerp(img[m], np.array([255, 255, 245.0]), rng.random(m.sum())[:, None])

    # soft clouds (horizontally stretched)
    if p.get("clouds", 0) > 0:
        n = noise2d(h, w, rng, 5, 2, stretch=3.0)
        c = np.clip((n - 0.52) * 3.5, 0, 1) * p["clouds"]
        c *= np.clip(1 - yy / (H * 0.95), 0, 1)
        img = lerp(img, np.array(p.get("cloudcol", (250, 238, 230)), np.float32), c[..., None] * 0.75)

    # mountain layers (far -> near)
    nl = len(p["mtns"])
    for i, (col, base, amp) in enumerate(p["mtns"]):
        ridge = (base + amp * noise1d(w, rng, 7, 2 + i)) * h
        mask = (yy > ridge[None, :]) & (yy < H + 2)
        shade = np.clip((yy - ridge[None, :]) / (0.3 * h), 0, 1)[..., None]
        c = np.array(col, np.float32)
        tex = noise2d(h, w, rng, 4, 8)[..., None]
        mc = lerp(c * 1.12, c * 0.82, shade) * (0.92 + 0.16 * tex)
        haze = p.get("haze", 0.35) * (nl - 1 - i) / max(1, nl - 1)
        mc = lerp(mc, bot, haze)
        img = np.where(mask[..., None], mc, img)

    # pine trees along the shoreline
    for _ in range(p.get("trees", 0)):
        side = rng.choice([-1, 1])
        x0 = (0.5 + side * rng.uniform(0.28, 0.5)) * w
        hgt = rng.uniform(0.1, 0.24) * h
        halfw = hgt * rng.uniform(0.18, 0.26)
        top_y = H - hgt
        rel = (yy - top_y) / hgt
        jag = 0.75 + 0.25 * np.abs(np.sin(rel * 22))
        m = (rel >= 0) & (rel <= 1.02) & (np.abs(xx - x0) < rel * halfw * jag)
        img = np.where(m[..., None], np.array(p.get("treecol", (22, 30, 38)), np.float32), img)

    # water / ground
    below = (yy >= H)[..., None]
    if p["mode"] == "lake":
        src = np.clip(2 * H - np.arange(h), 0, H - 1).astype(int)
        refl = img[src]
        ripple = noise2d(h, w, rng, 3, 10, stretch=6.0)
        off = ((ripple - 0.5) * p.get("ripple", 30)).astype(int)
        cols = np.clip(xx.astype(int) + off, 0, w - 1)
        refl2 = refl[yy.astype(int), cols]
        water = lerp(refl2 * 0.82, np.array(p["water"], np.float32), 0.3)
        img = np.where(below, water, img)
    elif p["mode"] == "sea":
        depth = np.clip((yy - H) / (h - H), 0, 1)[..., None]
        sea = lerp(lerp(bot, np.array(p["water"], np.float32), 0.6), np.array(p["water"], np.float32) * 0.7, depth)
        sparkle = noise2d(h, w, rng, 3, 14, stretch=8.0)
        streak = np.exp(-((xx - sx) / (0.06 * w + 0.25 * (yy - H))) ** 2)
        sea = lerp(sea, sc, (np.clip((sparkle - 0.5) * 4, 0, 1) * streak)[..., None] * 0.8)
        img = np.where(below, sea, img)
        sand_y = (0.86 + 0.04 * noise1d(w, rng, 4, 2)) * h
        sm = yy > sand_y[None, :]
        sand = np.array(p.get("sand", (214, 190, 160)), np.float32) * (0.9 + 0.1 * noise2d(h, w, rng, 3, 20))[..., None]
        img = np.where(sm[..., None], sand, img)
    else:  # meadow
        depth = np.clip((yy - H) / (h - H), 0, 1)[..., None]
        g = np.array(p["water"], np.float32)
        tex = noise2d(h, w, rng, 4, 12)[..., None]
        field = lerp(g * 1.1, g * 0.7, depth) * (0.85 + 0.3 * tex)
        img = np.where(below, field, img)

    # vignette + grain
    vx, vy = (xx / w - 0.5), (yy / h - 0.5)
    vig = 1 - 0.35 * (vx ** 2 + vy ** 2)
    img = img * vig[..., None]
    img += rng.normal(0, 2.2, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


PALETTES = {
    "sunset_lake": dict(mode="lake", horizon=0.62, top=(34, 56, 112), bottom=(238, 186, 142), skypow=0.9,
                        sun=(0.68, 0.50), sunr=0.045, suncol=(255, 226, 180), glow=0.22, clouds=0.9,
                        cloudcol=(246, 196, 170),
                        mtns=[((126, 112, 142), 0.36, 0.14), ((84, 76, 108), 0.46, 0.12), ((42, 40, 64), 0.55, 0.07)],
                        water=(40, 58, 96), trees=9, treecol=(20, 24, 36)),
    "day_lake": dict(mode="lake", horizon=0.6, top=(62, 118, 190), bottom=(196, 220, 238), sun=(0.22, 0.14),
                     sunr=0.03, suncol=(255, 252, 238), glow=0.15, glowamt=0.4, clouds=1.0, cloudcol=(252, 252, 250),
                     mtns=[((128, 152, 176), 0.30, 0.14), ((70, 108, 110), 0.42, 0.12), ((38, 70, 58), 0.52, 0.07)],
                     water=(50, 92, 120), trees=7, treecol=(24, 48, 38)),
    "misty": dict(mode="lake", horizon=0.64, top=(160, 172, 190), bottom=(228, 222, 212), sun=(0.5, 0.3), sunr=0.0,
                  suncol=(250, 245, 235), glow=0.3, glowamt=0.3,
                  mtns=[((170, 176, 188), 0.34, 0.12), ((128, 136, 154), 0.44, 0.1), ((82, 92, 110), 0.53, 0.08)],
                  water=(120, 130, 146), haze=0.5, trees=10, treecol=(48, 56, 66)),
    "night": dict(mode="lake", horizon=0.63, top=(8, 12, 34), bottom=(44, 54, 96), sun=(0.3, 0.22), sunr=0.03,
                  suncol=(236, 236, 226), glow=0.1, glowamt=0.35, stars=True,
                  mtns=[((40, 48, 84), 0.40, 0.12), ((24, 30, 58), 0.50, 0.08)], water=(12, 18, 40), trees=5,
                  treecol=(6, 8, 18)),
    "beach": dict(mode="sea", horizon=0.52, top=(70, 132, 200), bottom=(210, 228, 240), sun=(0.75, 0.2), sunr=0.03,
                  suncol=(255, 250, 235), glow=0.15, glowamt=0.4, clouds=0.7, cloudcol=(250, 250, 250), mtns=[],
                  water=(40, 110, 150)),
    "sunset_sea": dict(mode="sea", horizon=0.55, top=(52, 48, 104), bottom=(246, 170, 120), sun=(0.45, 0.47),
                       sunr=0.05, suncol=(255, 214, 160), glow=0.25, clouds=0.8, cloudcol=(236, 150, 140),
                       mtns=[((70, 56, 90), 0.49, 0.04)], water=(70, 60, 100), sand=(150, 110, 100)),
    "meadow": dict(mode="meadow", horizon=0.6, top=(80, 140, 205), bottom=(214, 228, 236), sun=(0.8, 0.15),
                   sunr=0.028, suncol=(255, 252, 240), glow=0.14, glowamt=0.35, clouds=1.0, cloudcol=(255, 255, 255),
                   mtns=[((120, 150, 160), 0.40, 0.14), ((92, 130, 90), 0.52, 0.06)], water=(110, 150, 70)),
    "dusk_hills": dict(mode="meadow", horizon=0.66, top=(40, 44, 96), bottom=(226, 150, 130), sun=(0.25, 0.55),
                       sunr=0.035, suncol=(255, 200, 150), glow=0.2,
                       mtns=[((110, 80, 110), 0.45, 0.12), ((60, 50, 80), 0.56, 0.08)], water=(60, 60, 70)),
}


def jitter(p, rng):
    q = dict(p)
    q["sun"] = (float(np.clip(p["sun"][0] + rng.uniform(-0.2, 0.2), 0.1, 0.9)), p["sun"][1])
    q["horizon"] = p["horizon"] + rng.uniform(-0.05, 0.05)
    shift = rng.uniform(-14, 14, 3)
    q["top"] = tuple(np.clip(np.array(p["top"]) + shift, 0, 255))
    return q


def main():
    # --- main photo + compressed copy ---
    photo = landscape(1500, 1000, 11, PALETTES["sunset_lake"])
    photo.save(OUT / "photo_original.jpg", quality=95, subsampling=0)
    photo.save(OUT / "photo_compressed.jpg", quality=14, optimize=True)
    for f in ("photo_original.jpg", "photo_compressed.jpg"):
        print(f, round((OUT / f).stat().st_size / 1024), "KB")

    # --- phone gallery: 4 columns x 7 rows ---
    rng = np.random.default_rng(3)
    names = list(PALETTES)
    t, gap, cols, rows = 150, 6, 4, 7
    gal = Image.new("RGB", (cols * t + (cols - 1) * gap, rows * t + (rows - 1) * gap), (255, 255, 255))
    for k in range(cols * rows):
        pal = jitter(PALETTES[names[(k * 3 + k // 4) % len(names)]], rng)
        im = landscape(240, 240, 100 + k, pal).resize((t, t), Image.LANCZOS)
        r, c = divmod(k, cols)
        gal.paste(im, (c * (t + gap), r * (t + gap)))
    gal.save(OUT / "gallery.png")
    print("gallery.png", gal.size)


if __name__ == "__main__":
    main()
