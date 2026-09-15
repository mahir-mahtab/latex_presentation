"""Images for Part 3.

1. img/mnist_*.png   real MNIST digits (test set), ink on transparent, for the slides
2. walk_frames/walk_NN.png   the latent-walk animation (demo-gif layout), built from
   the hand-drawn 4 -> 5 frames in 4_to_5_frames/

MNIST source: Google CVDF mirror (the one TensorFlow uses). Downloaded once into
<temp>/vae_mnist unless --mnist-dir points at existing .gz files.

    python gen_images.py [--mnist-dir DIR]
"""
import argparse, gzip, os, tempfile, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MIRROR = "https://storage.googleapis.com/cvdf-datasets/mnist/"
FILES = ("t10k-images-idx3-ubyte.gz", "t10k-labels-idx1-ubyte.gz")

# palette (CLAUDE.md)
NAVY, STEEL, SKY = (14, 35, 122), (77, 111, 173), (93, 173, 245)
TEAL, SLATE, PAPER, INK, WHITE = (63, 140, 138), (91, 100, 117), (251, 250, 247), (28, 34, 51), (255, 255, 255)


def tint(c, pct):  # TikZ-style  colour!pct  (mixed with white)
    return tuple(round(255 - (255 - v) * pct / 100) for v in c)


# ----------------------------------------------------------------- MNIST
def load_mnist(d):
    os.makedirs(d, exist_ok=True)
    for f in FILES:
        p = os.path.join(d, f)
        if not os.path.exists(p):
            urllib.request.urlretrieve(MIRROR + f, p)
    with gzip.open(os.path.join(d, FILES[0])) as f:
        X = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, 28, 28) / 255.0
    with gzip.open(os.path.join(d, FILES[1])) as f:
        y = np.frombuffer(f.read(), np.uint8, offset=8)
    return X, y


def slant(img):
    """horizontal shear of the stroke: + leans right (top to the right)."""
    ys, xs = np.mgrid[0:28, 0:28]
    w = img.sum()
    my, mx = (ys * img).sum() / w, (xs * img).sum() / w
    return -(((ys - my) * (xs - mx) * img).sum() / (((ys - my) ** 2) * img).sum())


def typical(X, y, c, n=400):
    """indices of the n most 'average-looking' digits of class c (clean, centred)."""
    idx = np.where(y == c)[0]
    m = X[idx].mean(0)
    d = ((X[idx] - m) ** 2).sum((1, 2))
    return idx[np.argsort(d)[:n]]


def pick(X, y, c, k=0, lean=None):
    idx = typical(X, y, c)
    if lean is None:
        return idx[k]
    s = np.array([slant(X[i]) for i in idx])
    return idx[np.argmin(np.abs(s - lean))]


def save_digit(img, name, alpha=1.0, blur=0.0, size=168):
    g = Image.fromarray((img * 255).astype(np.uint8))
    if blur:
        g = g.filter(ImageFilter.GaussianBlur(blur))
        g = Image.fromarray((np.asarray(g) * 0.8).astype(np.uint8))
    g = g.resize((size, size), Image.LANCZOS)
    a = (np.asarray(g, float) * alpha).clip(0, 255).astype(np.uint8)
    rgba = np.zeros((size, size, 4), np.uint8)
    rgba[..., :3] = INK
    rgba[..., 3] = a
    Image.fromarray(rgba, "RGBA").save(os.path.join(HERE, "img", name + ".png"))


def make_digits(X, y):
    os.makedirs(os.path.join(HERE, "img"), exist_ok=True)
    out = {
        "mnist_0": pick(X, y, 0), "mnist_1": pick(X, y, 1), "mnist_2": pick(X, y, 2),
        "mnist_3": pick(X, y, 3), "mnist_3b": pick(X, y, 3, 25), "mnist_4": pick(X, y, 4),
        "mnist_5": pick(X, y, 5), "mnist_6": pick(X, y, 6), "mnist_7": pick(X, y, 7),
        "mnist_8": pick(X, y, 8), "mnist_8b": pick(X, y, 8, 25), "mnist_9": pick(X, y, 9),
        # same class, different style (slant): used for "only the style changes" and beta-VAE
        "mnist_7_l": pick(X, y, 7, lean=-0.31), "mnist_7_m": pick(X, y, 7, lean=0.02),
        "mnist_7_r": pick(X, y, 7, lean=0.40),
        "mnist_1_l": pick(X, y, 1, lean=-0.03), "mnist_1_m": pick(X, y, 1, lean=0.20),
        "mnist_1_r": pick(X, y, 1, lean=0.43),
    }
    for name, i in out.items():
        save_digit(X[i], name)
    save_digit(X[out["mnist_7"]], "mnist_7_recon", blur=0.9)          # blurry reconstruction
    save_digit(X[out["mnist_7_m"]], "mnist_7_m_recon", blur=0.9)
    save_digit(X[out["mnist_2"]], "mnist_2_light", alpha=0.4)         # faded augmentation copies
    for c in (3, 8, 1, 6):
        save_digit(X[out[f"mnist_{c}"]], f"mnist_{c}_light", alpha=0.35)
    print("digits:", ", ".join(out))


# ----------------------------------------------------------------- walk animation
N_FRAMES = 31
SS = 2                      # supersampling
W, H = 1400, 620            # 100 px = 1 cm on the slide (14 x 6.2 cm)
FONT_DIR = os.path.join(os.environ.get("APPDATA", ""), "MiKTeX", "fonts", "opentype", "ibm", "plex")


def font(style, px):
    for f in (f"IBMPlexSerif-{style}.otf",):
        p = os.path.join(FONT_DIR, f)
        if os.path.exists(p):
            return ImageFont.truetype(p, px * SS)
    return ImageFont.load_default()


def ease(t):
    return t * t * (3 - 2 * t)


def load_morph():
    frames = []
    for i in range(1, 11):
        a = np.asarray(Image.open(os.path.join(HERE, "4_to_5_frames", f"frame_{i:02d}.png")).convert("RGBA"))[..., 3]
        frames.append(a.astype(float) / 255)
    return frames


def morph_at(frames, t):
    pos = t * (len(frames) - 1)
    k = min(int(pos), len(frames) - 2)
    return frames[k + 1] if pos - k >= 0.5 else frames[k]   # hard cut: every frame is a clean drawing


def make_walk(X, y):
    out_dir = os.path.join(HERE, "walk_frames")
    os.makedirs(out_dir, exist_ok=True)
    morph = load_morph()
    thumb4 = Image.open(os.path.join(HERE, "img", "mnist_4.png"))
    thumb5 = Image.open(os.path.join(HERE, "img", "mnist_5.png"))
    f_lbl, f_z, f_sub = font("Regular", 30), font("Italic", 42), font("Italic", 28)
    S = lambda *v: tuple(int(round(x * SS)) for x in v)

    # latent panel geometry (px); 1 latent unit = 95 px
    px0, py0, px1, py1 = 20, 30, 660, 590
    cx, cy, u = (px0 + px1) / 2, (py0 + py1) / 2, 95
    P = lambda a, b: (cx + a * u, cy - b * u)
    A, B = (-1.85, -0.95), (1.75, 0.95)

    rng = np.random.RandomState(31)
    blobs = [(A, STEEL), (B, TEAL), ((-1.9, 1.45), tint(SLATE, 55)), ((0.2, 1.75), tint(SLATE, 35)),
             ((2.35, -1.45), tint(STEEL, 45)), ((-0.05, 0.0), tint(TEAL, 40)), ((0.6, -1.9), tint(SLATE, 40))]
    dots = [(P(c[0] + 0.3 * r * np.cos(th), c[1] + 0.3 * r * np.sin(th)), col)
            for c, col in blobs for r, th in zip(np.minimum(2.0, np.sqrt(-2 * np.log(np.maximum(rng.rand(26), .01)))),
                                                 2 * np.pi * rng.rand(26))]

    for i in range(N_FRAMES):
        t = ease(i / (N_FRAMES - 1))
        img = Image.new("RGB", S(W, H), PAPER)
        d = ImageDraw.Draw(img)

        # ---- latent panel ----
        d.rectangle(S(px0, py0, px1, py1), fill=WHITE)
        for gx in np.arange(cx % 47.5, px1, 47.5):
            if gx > px0: d.line(S(gx, py0, gx, py1), fill=tint(SLATE, 12), width=SS)
        for gy in np.arange(cy % 47.5, py1, 47.5):
            if gy > py0: d.line(S(px0, gy, px1, gy), fill=tint(SLATE, 12), width=SS)
        d.line(S(px0, cy, px1, cy), fill=tint(SLATE, 30), width=SS)
        d.line(S(cx, py0, cx, py1), fill=tint(SLATE, 30), width=SS)
        for (x, yy), col in dots:
            if px0 + 6 < x < px1 - 6 and py0 + 6 < yy < py1 - 6:
                d.ellipse(S(x - 4.5, yy - 4.5, x + 4.5, yy + 4.5), fill=col)
        d.rectangle(S(px0, py0, px1, py1), outline=tint(SLATE, 50), width=2 * SS)
        tb = d.textbbox(S(px0 + 12, py0 + 8), "latent space", font=f_lbl)
        d.rectangle((tb[0] - 4 * SS, tb[1] - 3 * SS, tb[2] + 4 * SS, tb[3] + 3 * SS), fill=WHITE)
        d.text(S(px0 + 12, py0 + 8), "latent space", font=f_lbl, fill=SLATE)

        # digit thumbnails next to the two clusters
        for th, (a, b) in ((thumb4, (-2.45, -2.1)), (thumb5, (2.55, 1.95))):
            x, yy = P(a, b)
            d.rectangle(S(x - 30, yy - 30, x + 30, yy + 30), fill=WHITE, outline=tint(SLATE, 50), width=SS)
            tt = th.resize(S(58, 58), Image.LANCZOS)
            img.paste(tt, S(x - 29, yy - 29), tt)

        # dashed path, solid trail up to the current point, moving marker
        ax, ay = P(*A); bx, by = P(*B)
        n = 26
        for s in range(0, n, 2):
            d.line(S(ax + (bx - ax) * s / n, ay + (by - ay) * s / n,
                     ax + (bx - ax) * (s + 1) / n, ay + (by - ay) * (s + 1) / n), fill=NAVY, width=3 * SS)
        mx, my = ax + (bx - ax) * t, ay + (by - ay) * t
        d.line(S(ax, ay, mx, my), fill=NAVY, width=5 * SS)
        for (x, yy) in ((ax, ay), (bx, by)):
            d.ellipse(S(x - 8, yy - 8, x + 8, yy + 8), fill=NAVY, outline=WHITE, width=2 * SS)
        d.ellipse(S(mx - 15, my - 15, mx + 15, my + 15), fill=WHITE, outline=NAVY, width=5 * SS)
        d.ellipse(S(mx - 6, my - 6, mx + 6, my + 6), fill=TEAL)
        d.text(S(ax + 8, ay + 8), "z", font=f_z, fill=NAVY)
        d.text(S(ax + 30, ay + 32), "a", font=f_sub, fill=NAVY)
        d.text(S(bx + 16, by - 4), "z", font=f_z, fill=NAVY)
        d.text(S(bx + 38, by + 20), "b", font=f_sub, fill=NAVY)

        # ---- decoder ----
        d.line(S(px1 + 14, cy, 745, cy), fill=SLATE, width=2 * SS)
        d.polygon(S(745, cy - 8, 745, cy + 8, 760, cy), fill=SLATE)
        d.polygon(S(765, cy - 55, 880, cy - 115, 880, cy + 115, 765, cy + 55), fill=tint(TEAL, 10), outline=TEAL, width=3 * SS)
        tb = d.textbbox((0, 0), "decoder", font=f_lbl)
        d.text(S(822.5 - (tb[2] - tb[0]) / (2 * SS), cy + 130), "decoder", font=f_lbl, fill=tuple(int(v * .7) for v in TEAL))
        d.line(S(890, cy, 930, cy), fill=SLATE, width=2 * SS)
        d.polygon(S(930, cy - 8, 930, cy + 8, 945, cy), fill=SLATE)

        # ---- decoded output ----
        bx0, by0, bx1, by1 = 955, 90, 1375, 510
        d.rectangle(S(bx0, by0, bx1, by1), fill=WHITE, outline=tint(SLATE, 50), width=2 * SS)
        a = morph_at(morph, t)
        side = (bx1 - bx0 - 30) * SS
        g = Image.fromarray((a * 255).astype(np.uint8)).resize((side, side), Image.LANCZOS)
        ink = Image.new("RGB", (side, side), INK)
        img.paste(ink, S(bx0 + 15, by0 + 15), g)
        tb = d.textbbox((0, 0), "decoder output", font=f_lbl)
        d.text(S((bx0 + bx1) / 2 - (tb[2] - tb[0]) / (2 * SS), by0 - 48), "decoder output", font=f_lbl, fill=SLATE)

        # progress bar under the output: how far along the line we are
        d.rectangle(S(bx0, by1 + 26, bx1, by1 + 32), fill=tint(SLATE, 20))
        d.rectangle(S(bx0, by1 + 26, bx0 + (bx1 - bx0) * t, by1 + 32), fill=NAVY)

        img.resize((W, H), Image.LANCZOS).quantize(colors=96, method=Image.MEDIANCUT).save(
            os.path.join(out_dir, f"walk_{i + 1:02d}.png"), optimize=True)
    print("walk frames:", N_FRAMES)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mnist-dir", default=os.path.join(tempfile.gettempdir(), "vae_mnist"))
    args = ap.parse_args()
    X, y = load_mnist(args.mnist_dir)
    make_digits(X, y)
    make_walk(X, y)
