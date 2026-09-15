"""Convert Phosphor duotone SVG icons (MIT licence) into TikZ macros.
Every path is flattened to absolute moves, lines and cubic Beziers (arcs converted),
normalised to a 1 x 1 cm box centred on the origin, y up."""
import re, glob, os, math
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def tokens(d):
    for m in re.finditer(r'[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?', d):
        yield m.group()

def arc_to_beziers(x1, y1, rx, ry, phi, fa, fs, x2, y2):
    if rx == 0 or ry == 0:
        return [(x1, y1, x2, y2, x2, y2)]
    phi = math.radians(phi)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = x1p**2 / rx**2 + y1p**2 / ry**2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2
    den = rx**2 * y1p**2 + ry**2 * x1p**2
    co = math.sqrt(max(0, num / den)) if den else 0
    if fa == fs:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2
    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    n = max(1, math.ceil(abs(dt) / (math.pi / 2) - 1e-9))
    seg = dt / n
    k = 4 / 3 * math.tan(seg / 4)
    out = []
    def pt(t):
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        return cp * ex - sp * ey + cx, sp * ex + cp * ey + cy
    def dpt(t):
        ex, ey = -rx * math.sin(t), ry * math.cos(t)
        return cp * ex - sp * ey, sp * ex + cp * ey
    for i in range(n):
        ta, tb = t1 + i * seg, t1 + (i + 1) * seg
        pa, pb = pt(ta), pt(tb)
        da, db = dpt(ta), dpt(tb)
        out.append((pa[0] + k * da[0], pa[1] + k * da[1], pb[0] - k * db[0], pb[1] - k * db[1], pb[0], pb[1]))
    return out

def to_tikz(d):
    tk = list(tokens(d))
    i, cmd = 0, None
    cx = cy = sx = sy = 0.0
    lcx = lcy = None   # last cubic control point (for S)
    parts = []
    P = lambda x, y: '(%.4f,%.4f)' % ((x - 128) / 256, (128 - y) / 256)
    def num():
        nonlocal i
        v = float(tk[i]); i += 1
        return v
    while i < len(tk):
        if re.match(r'[A-Za-z]', tk[i]):
            cmd = tk[i]; i += 1
        c, rel = cmd.upper(), cmd.islower()
        if c == 'Z':
            parts.append('-- cycle'); cx, cy = sx, sy; lcx = None
            continue
        if c == 'M':
            x, y = num(), num()
            if rel: x, y = x + cx, y + cy
            parts.append(P(x, y)); cx, cy = sx, sy = x, y
            cmd = 'l' if rel else 'L'; lcx = None
        elif c in 'LHV':
            if c == 'L':
                x, y = num(), num()
                if rel: x, y = x + cx, y + cy
            elif c == 'H':
                x = num() + (cx if rel else 0); y = cy
            else:
                y = num() + (cy if rel else 0); x = cx
            parts.append('-- ' + P(x, y)); cx, cy = x, y; lcx = None
        elif c in 'CS':
            if c == 'C':
                x1, y1 = num(), num()
                if rel: x1, y1 = x1 + cx, y1 + cy
            else:
                x1, y1 = (2 * cx - lcx, 2 * cy - lcy) if lcx is not None else (cx, cy)
            x2, y2, x, y = num(), num(), num(), num()
            if rel: x2, y2, x, y = x2 + cx, y2 + cy, x + cx, y + cy
            parts.append('.. controls %s and %s .. %s' % (P(x1, y1), P(x2, y2), P(x, y)))
            lcx, lcy = x2, y2; cx, cy = x, y
        elif c == 'A':
            rx, ry, phi, fa, fs, x, y = [num() for _ in range(7)]
            if rel: x, y = x + cx, y + cy
            for b in arc_to_beziers(cx, cy, rx, ry, phi, int(fa), int(fs), x, y):
                parts.append('.. controls %s and %s .. %s' % (P(b[0], b[1]), P(b[2], b[3]), P(b[4], b[5])))
            cx, cy = x, y; lcx = None
        else:
            raise ValueError('unsupported command ' + cmd)
    return ' '.join(parts)

out = []
for f in sorted(glob.glob('*.svg')):
    s = open(f).read()
    paths = re.findall(r'<path d="([^"]+)"( opacity)?', s)
    name = os.path.basename(f).replace('-duotone.svg', '').replace('-', '')
    bg = ' '.join(to_tikz(d) for d, o in paths if o)
    fg = ' '.join(to_tikz(d) for d, o in paths if not o)
    out.append('% Phosphor icon "' + f[:-4] + '" (MIT licence), 1x1 cm centred on the origin\n'
               + '\\newcommand{\\ic' + name + '}[2]{%\n'
               + '  \\fill[#2] ' + bg + ';\n'
               + '  \\fill[#1,even odd rule] ' + fg + ';}')
open('icons.tex', 'w', newline='\n').write('\n'.join(out) + '\n')
print('ok', len(out))
