#!/usr/bin/env python3
"""kw3_11 ("nonessential") rev2: HERO IMAGE (suitcase sorting scene) + calm vaporwave backdrop + Bauhaus + line animation.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-23-cnn python3 render_kw3_11.py            (full render)
       NEWS_ROOT=... python3 render_kw3_11.py --frames 0 0.3 1.0 ...                           (PNG stills only)
Inputs: 03_script/keyword_scripts_v3.json, audio/v3/kw3_11.mp3, audio/words_kw_v3.json, 02_bento/cards.json (card 3).
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-23-cnn")
RID = "11"
OUT = f"{ROOT}/06_keyword_reels/v3"; FR = f"{OUT}/frames"
W, H, FPS = 1080, 1920, 30
TAIL = 0.7
J = lambda p: json.load(open(f"{ROOT}/{p}"))
SC = {r["id"]: r for r in J("03_script/keyword_scripts_v3.json")["reels"]}[RID]
WK = J("audio/words_kw_v3.json")[RID]
WORDS = WK["words"]; BEATS = WK["beats"]
CARD = {c["card"]: c for c in J("02_bento/cards.json")}[3]["colors"]
MP3 = f"{ROOT}/audio/v3/kw3_{RID}.mp3"

# ---- palette: card 3 (sky blue / scarlet / cloud white / navy) pushed to vaporwave + bauhaus primaries
def hx(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
SKY = hx(CARD["background"]); SCARLET = hx(CARD["cell_A"]["bg"]); CLOUD = hx("#F8FAFC"); NAVY = hx(CARD["cell_C"]["bg"])
INK = hx(CARD["head_and_handle"])           # #0B1A2A
YEL = (255, 212, 0); BLK = (14, 14, 18); MAG = (255, 60, 190); CYAN = (40, 230, 255); WHITE = (255, 255, 255)
DIMKO = hx(CARD["cell_C"]["ko"])

FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FBOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size, index=1)
    return _fc[k]
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def e_out(p): return 1 - (1 - p) ** 3
def e_back(p, c=1.70158): q = p - 1; return 1 + (c + 1) * q ** 3 + c * q ** 2
def e_io(p): return 0.5 - 0.5 * math.cos(math.pi * clamp(p))
def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + 0.05) / (lb + 0.05)

# ---------------------------------------------------------------- background (vaporwave)
HOR = 1360; SUNC = (450, 1126); SUNR = 232
def _lerp_stops(y, ys, cols):
    return np.stack([np.interp(y, ys, [c[i] for c in cols]) for i in range(3)], -1)
def build_bg():
    yy = np.arange(HOR, dtype=np.float64)
    sky = _lerp_stops(yy, [0, 480, 840, 1150, HOR], [(14, 28, 52), (40, 22, 98), (118, 30, 150), (255, 70, 170), (255, 150, 110)])
    sky = np.repeat(sky[:, None, :], W, 1)
    gy, gx = np.mgrid[0:HOR, 0:W]
    r = np.hypot(gx - SUNC[0], gy - SUNC[1]); glow = np.clip(1 - r / 620, 0, 1) ** 2.2
    sky = sky + glow[..., None] * np.array([150, 40, 120]) * 0.55
    # floor
    fy = np.arange(H - HOR, dtype=np.float64)
    fl = _lerp_stops(fy, [0, 120, H - HOR], [(130, 28, 140), (50, 14, 90), (18, 8, 44)])
    fl = np.repeat(fl[:, None, :], W, 1)
    d = (np.arange(H - HOR, dtype=np.float64) + 1.0)[:, None]
    u = (np.arange(W, dtype=np.float64)[None, :] - 450) / d * 4.0
    du = np.abs((u + 0.5) % 1 - 0.5); px = du * d / 4.0
    th = 1.4 + d * 0.007
    va = np.clip(1 - px / th, 0, 1) + np.clip(1 - px / (th * 4.5), 0, 1) ** 2 * 0.35
    va *= np.clip(d / 70, 0, 1) ** 1.5
    vcol = va[..., None] * np.array(CYAN, np.float64)
    # sun gradient + mask
    sy0 = SUNC[1] - SUNR; sy1 = SUNC[1] + SUNR; sx0 = SUNC[0] - SUNR
    yy2, xx2 = np.mgrid[sy0:sy1, sx0:sx0 + 2 * SUNR]
    rr = np.hypot(xx2 - SUNC[0] + 0.5, yy2 - SUNC[1] + 0.5)
    sm = np.clip(SUNR - rr + 0.5, 0, 1)
    t = (yy2 - sy0) / (2 * SUNR)
    sun = _lerp_stops(t, [0, 0.45, 1.0], [(255, 236, 90), (255, 140, 120), (255, 40, 170)])
    return dict(sky=sky, fl=fl, vcol=vcol, d=d, sm=sm, sun=sun, sy0=sy0, sx0=sx0, yy2=yy2)
BG = build_bg()
rng = np.random.default_rng(7)
STARS = [(int(rng.integers(40, W - 40)), int(rng.integers(260, 820)), rng.random() * 6.28, int(rng.integers(0, 3))) for _ in range(34)]

def make_bg(now):
    b = BG; fr = np.empty((H, W, 3), np.float64)
    top = b["sky"].copy()
    # striped sun (gaps widen toward the bottom and scroll down)
    rel = b["yy2"] - (SUNC[1] - 70)
    per = 38.0; ph = (rel - now * 16) % per
    gap = np.clip(rel * 0.075, 0, 30)
    keep = ((rel < 0) | (ph > gap)).astype(np.float64)
    a = (b["sm"] * keep)[..., None]
    ys0, xs0 = b["sy0"], b["sx0"]; h2, w2 = a.shape[:2]
    reg = top[ys0:ys0 + h2, xs0:xs0 + w2]
    top[ys0:ys0 + h2, xs0:xs0 + w2] = reg * (1 - a) + b["sun"] * a
    for (sx, sy, ph0, k) in STARS:
        v = 150 + 60 * (0.5 + 0.5 * math.sin(now * 1.5 + ph0))
        top[sy - 1:sy + 2, sx - 1:sx + 2] = (v, v, v)
        if k == 2: top[sy, sx - 5:sx + 6] = (v, v, v); top[sy - 5:sy + 6, sx] = (v, v, v)
    fr[:HOR] = top
    # floor: horizontal lines flow toward the viewer
    d = b["d"]; s = 420.0 / d - now * 0.9
    dist = np.minimum(s % 1, 1 - (s % 1)) * d * d / 420.0
    th = 1.5 + d * 0.008
    ha = (np.clip(1 - dist / th, 0, 1) + np.clip(1 - dist / (th * 4.5), 0, 1) ** 2 * 0.4) * np.clip(d / 100, 0, 1) ** 1.5
    fl = b["fl"] + b["vcol"] * 0.38 + ha[..., None] * np.array(MAG, np.float64)[None, None, :] * 0.42
    fr[HOR:] = fl
    fr[HOR - 2:HOR + 2] = (255, 190, 235)
    return np.clip(fr, 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- sprites
_tc = {}
def tsprite(text, size, mode="chrome", fill=WHITE, stroke=0, scol=INK, fnt=FB):
    key = (text, size, mode, fill, stroke, scol, fnt)
    if key in _tc: return _tc[key]
    f = font(fnt, size); asc, desc = f.getmetrics(); w = int(math.ceil(f.getlength(text)))
    pad = stroke + 6; Wd, Hd = w + 2 * pad, asc + desc + 2 * pad
    S = Image.new("L", (Wd, Hd), 0); F = Image.new("L", (Wd, Hd), 0)
    sw = 3 if mode == "ghost" else stroke
    ImageDraw.Draw(S).text((pad, pad), text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    ImageDraw.Draw(F).text((pad, pad), text, font=f, fill=255)
    s = np.array(S) / 255.0; fm = np.array(F) / 255.0
    arr = np.zeros((Hd, Wd, 4), np.float64)
    if mode == "ghost":
        ring = np.clip(s - fm, 0, 1); arr[..., :3] = fill; arr[..., 3] = np.maximum(ring * 255, fm * 80)
    else:
        t = ((np.arange(Hd) - pad) / max(1, asc + desc))[:, None]
        if mode == "chrome":
            g = _lerp_stops(np.clip(t, 0, 1)[:, 0], [0, 0.5, 1.0], [(255, 255, 255), (150, 228, 255), (255, 160, 228)])
            col = np.repeat(g[:, None, :], Wd, 1)
        else:
            col = np.zeros((Hd, Wd, 3)) + np.array(fill)
        base = np.zeros((Hd, Wd, 3)) + np.array(scol)
        arr[..., :3] = base * (1 - fm[..., None]) + col * fm[..., None]
        arr[..., 3] = np.maximum(s, fm) * 255
    im = Image.fromarray(arr.astype(np.uint8), "RGBA"); _tc[key] = im; return im

SHX = SHY = 0
def blit(img, spr, cx, cy, scale=1.0, rot=0.0, alpha=1.0, shake=True):
    if alpha <= 0.003: return
    s = spr
    if abs(scale - 1) > 1e-3: s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BILINEAR)
    if rot: s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        s = s.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    ox, oy = (SHX, SHY) if shake else (0, 0)
    img.paste(s, (int(cx - s.width / 2 + ox), int(cy - s.height / 2 + oy)), s)

_sc = {}
def shape_sprite(kind, size, col, rot):
    rq = int(round(rot / 2.0) * 2) % 360; key = (kind, size, col, rq)
    if key in _sc: return _sc[key]
    SS = 3
    if kind == "bar": bw, bh = size; side = int(math.hypot(bw, bh)) + 8
    else: side = int(size * 1.45) + 8
    im = Image.new("RGBA", (side * SS, side * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = side * SS / 2
    a = math.radians(rq)
    def rp(pts): return [(c + (x * math.cos(a) - y * math.sin(a)), c + (x * math.sin(a) + y * math.cos(a))) for x, y in pts]
    R = (0 if kind == "bar" else size * SS / 2)
    if kind == "circle": d.ellipse((c - R, c - R, c + R, c + R), fill=col)
    elif kind == "ring": d.ellipse((c - R, c - R, c + R, c + R), outline=col, width=int(size * SS * 0.1))
    elif kind == "square": d.polygon(rp([(-R, -R), (R, -R), (R, R), (-R, R)]), fill=col)
    elif kind == "tri": d.polygon(rp([(0, -R * 1.05), (R * 1.05, R * 0.8), (-R * 1.05, R * 0.8)]), fill=col)
    elif kind == "half":
        n = 60; pts = [(R * math.cos(math.pi * i / n + math.pi), R * math.sin(math.pi * i / n + math.pi) * 1.0 + R * 0.5) for i in range(n + 1)]
        d.polygon(rp(pts), fill=col)
    elif kind == "bar":
        bw, bh = size; d.polygon(rp([(-bw * SS / 2, -bh * SS / 2), (bw * SS / 2, -bh * SS / 2), (bw * SS / 2, bh * SS / 2), (-bw * SS / 2, bh * SS / 2)]), fill=col)
    im = im.resize((side, side), Image.LANCZOS); _sc[key] = im; return im

def draw_shapes(img, now, t0, items):
    for i, it in enumerate(items):
        kind, size, col, x, y, r0, spin, ox, oy = it
        p = clamp((now - t0 - i * 0.06) / 0.5)
        if p <= 0: continue
        e = e_back(p)
        cx = x + ox * (1 - e) + 6 * math.sin(now * 1.3 + i); cy = y + oy * (1 - e) + 6 * math.cos(now * 1.1 + i * 2)
        blit(img, shape_sprite(kind, size, col, r0 + spin * (now - t0)), cx, cy, alpha=min(1, p * 3))

def pline(img, pts, width, col, frac, outline=None, closed=False):
    """stroke-reveal polyline: draws the first `frac` of its length."""
    frac = clamp(frac)
    if frac <= 0: return
    P = [np.array(p, float) for p in pts]
    if closed: P.append(P[0])
    seg = [np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1)]; tot = sum(seg); tgt = frac * tot
    out = [P[0]]; acc = 0
    for i, sl in enumerate(seg):
        if acc + sl <= tgt: out.append(P[i + 1]); acc += sl
        else:
            out.append(P[i] + (P[i + 1] - P[i]) * ((tgt - acc) / max(sl, 1e-6))); break
    A = np.array(out); pad = int(width + (outline or 0)) + 6
    x0, y0 = A.min(0).astype(int) - pad; x1, y1 = A.max(0).astype(int) + pad
    SS = 3; im = Image.new("RGBA", ((x1 - x0) * SS, (y1 - y0) * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def stroke(w, c):
        pp = [((x - x0) * SS, (y - y0) * SS) for x, y in A]
        d.line(pp, fill=c, width=int(w * SS), joint="curve")
        for (x, y) in (pp[0], pp[-1]) + tuple(pp[1:-1]):
            r = w * SS / 2; d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    if outline: stroke(width + outline * 2, WHITE + (255,))
    stroke(width, col + (255,))
    im = im.resize((x1 - x0, y1 - y0), Image.LANCZOS); img.paste(im, (x0 + SHX, y0 + SHY), im)

def ellipse_pts(cx, cy, rx, ry, a0=-90, n=96):
    return [(cx + rx * math.cos(math.radians(a0 + 360 * i / n)), cy + ry * math.sin(math.radians(a0 + 360 * i / n))) for i in range(n + 1)]
def zigzag(x0, x1, y, amp, n):
    return [(x0 + (x1 - x0) * i / n, y + (amp if i % 2 else -amp)) for i in range(n + 1)]

def rect(img, x0, y0, x1, y1, col, alpha=1.0):
    x0 += SHX; x1 += SHX; y0 += SHY; y1 += SHY
    if x1 <= x0 or y1 <= y0: return
    if alpha >= 1: ImageDraw.Draw(img).rectangle((x0, y0, x1, y1), fill=col)
    else: img.paste(col, (int(x0), int(y0), int(x1), int(y1)), Image.new("L", (int(x1) - int(x0), int(y1) - int(y0)), int(255 * alpha)))

def band(img, x0, y0, w, h, wipe, now):
    wp = int(w * clamp(wipe))
    if wp <= 0: return
    xs = np.arange(wp)[None, :]; ys = np.arange(h)[:, None]
    pat = (((xs + ys + int(now * 70)) // 26) % 2)[..., None]
    arr = np.where(pat == 1, np.array(YEL), np.array(BLK)).astype(np.uint8)
    img.paste(Image.fromarray(arr), (x0 + SHX, y0 + SHY))

def fit_size(tokens, maxw, size, gap=0.22, fnt=FB, lo=36):
    while size > lo:
        f = font(fnt, size)
        if sum(f.getlength(t) for t in tokens) + gap * size * (len(tokens) - 1) <= maxw: break
        size -= 2
    return size
def row(tokens, size, cx=None, x0=None, gap=0.22, fnt=FB):
    f = font(fnt, size); ws = [f.getlength(t) for t in tokens]; g = gap * size
    tot = sum(ws) + g * (len(tokens) - 1); x = (cx - tot / 2) if cx is not None else x0
    out = []
    for t, w in zip(tokens, ws): out.append((t, x + w / 2, w)); x += w + g
    return out, tot

def slam(img, now, s, spr, cx, cy, ghost=None, p0=0.0, dur=0.22, sign=1):
    p = clamp((now - s) / dur + p0)
    if p <= 0:
        if ghost is not None: blit(img, ghost, cx, cy)
        return
    e = e_out(p); blit(img, spr, cx, cy, scale=1 + 0.9 * (1 - e), rot=7 * (1 - e) * sign, alpha=min(1, p * 4))
def slide(img, now, s, spr, cx, cy, dx, dur=0.3):
    if now < s: return
    p = e_out(clamp((now - s) / dur)); blit(img, spr, cx + dx * (1 - p), cy, alpha=p)

# ---------------------------------------------------------------- timing
BS = {b["role"]: b["start"] for b in BEATS}
BE = {b["role"]: b for b in BEATS}
WT = lambda i: WORDS[i]["s"]
CUTS = [b["start"] for b in BEATS]
PAY = BE["payoff"]; EXPR_S, EXPR_E, SAVE_S = PAY["expr_start"], PAY["expr_end"], PAY["save_start"]
TE = WT(15)            # Scribe start of "nonessential" in the term beat -> x items fly out
SHX = SHY = 0
def beat_index(now):
    i = 0
    for k, t in enumerate(CUTS):
        if now >= t - 1e-6: i = k
    return i

# ---------------------------------------------------------------- hero image sprites (Bauhaus primitives, SS=3 antialias)
SKY2 = (77, 176, 232)
class P:
    def __init__(s, d, SS): s.d = d; s.S = SS
    def _p(s, pts): return [(x * s.S, y * s.S) for x, y in pts]
    def rrect(s, x0, y0, x1, y1, r, fill, outline=None, ow=0):
        s.d.rounded_rectangle((x0 * s.S, y0 * s.S, x1 * s.S, y1 * s.S), r * s.S, fill=fill, outline=outline, width=int(ow * s.S))
    def rect(s, x0, y0, x1, y1, fill, outline=None, ow=0): s.rrect(x0, y0, x1, y1, 0, fill, outline, ow)
    def ell(s, x0, y0, x1, y1, fill, outline=None, ow=0):
        s.d.ellipse((x0 * s.S, y0 * s.S, x1 * s.S, y1 * s.S), fill=fill, outline=outline, width=int(ow * s.S))
    def poly(s, pts, fill, outline=None, ow=0):
        pp = s._p(pts); s.d.polygon(pp, fill=fill)
        if outline: s.d.line(pp + [pp[0]], fill=outline, width=int(ow * s.S), joint="curve")
    def line(s, pts, w, fill):
        pp = s._p(pts); s.d.line(pp, fill=fill, width=int(w * s.S), joint="curve")
        r = w * s.S / 2
        for x, y in pp: s.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)
    def text(s, x, y, t, size, fill, fnt=FB, anchor="mm"):
        s.d.text((x * s.S, y * s.S), t, font=font(fnt, size * s.S), fill=fill, anchor=anchor)
def mk(w, h, fn, SS=3):
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0)); fn(P(ImageDraw.Draw(im), SS)); return im.resize((w, h), Image.LANCZOS)

def _bottle(p):
    p.rrect(20, 2, 50, 24, 5, SCARLET, INK, 4); p.rrect(8, 30, 62, 176, 16, SKY, INK, 5); p.rect(12, 88, 58, 132, CLOUD)
    p.poly([(35, 96), (47, 116), (23, 116)], SKY2); p.ell(23, 104, 47, 128, SKY2)
def _idcard(p):
    p.rrect(3, 3, 147, 97, 10, CLOUD, INK, 5); p.rect(8, 8, 142, 26, SKY); p.ell(22, 34, 48, 60, INK); p.ell(14, 62, 56, 94, INK)
    p.rect(70, 40, 136, 50, INK); p.rect(70, 58, 118, 66, INK); p.rect(70, 74, 128, 82, SCARLET)
def _medkit(p):
    p.rrect(40, 3, 90, 32, 8, CLOUD, INK, 5); p.rrect(3, 16, 127, 107, 12, CLOUD, INK, 5)
    p.rect(55, 36, 75, 88, SCARLET); p.rect(39, 52, 91, 72, SCARLET)
def _console(p):
    p.rrect(22, 2, 62, 16, 5, NAVY, INK, 3); p.rrect(130, 2, 170, 16, 5, NAVY, INK, 3)
    p.rrect(3, 10, 187, 112, 28, NAVY, INK, 5); p.rrect(58, 26, 132, 80, 6, SKY, CLOUD, 4)
    p.rect(16, 54, 46, 66, CLOUD); p.rect(25, 45, 37, 75, CLOUD)
    p.ell(146, 40, 168, 62, SCARLET); p.ell(158, 62, 180, 84, YEL); p.rect(70, 92, 120, 98, CLOUD)
def _souvenir(p):
    p.poly([(22, 166), (108, 166), (96, 126), (34, 126)], SCARLET, INK, 4)
    p.ell(7, 7, 123, 123, SKY, INK, 5); p.poly([(28, 102), (65, 44), (102, 102)], CLOUD, INK, 3); p.ell(84, 24, 104, 44, YEL)
def _shoe(p):
    p.poly([(14, 72), (14, 16), (70, 16), (100, 48), (150, 56), (184, 72)], SCARLET, INK, 5)
    p.rrect(4, 68, 186, 92, 10, NAVY, INK, 4)
    for k in range(3): p.line([(40 + 20 * k, 26 + 7 * k), (66 + 20 * k, 40 + 7 * k)], 5, CLOUD)
def _check(p):
    p.ell(3, 3, 57, 57, SKY, WHITE, 5); p.line([(17, 31), (26, 41), (44, 19)], 9, INK)
def _cross(p):
    p.ell(3, 3, 57, 57, SCARLET, WHITE, 5); p.line([(19, 19), (41, 41)], 9, WHITE); p.line([(41, 19), (19, 41)], 9, WHITE)
def _lid(p):
    p.rrect(3, 3, 327, 167, 18, NAVY, INK, 5); p.rrect(18, 18, 312, 152, 10, SKY)
    p.rect(18, 112, 312, 126, SKY2); p.rect(18, 134, 312, 152, CLOUD)
def _body_back(p):
    p.rrect(3, 3, 447, 337, 26, SCARLET, INK, 6); p.rrect(22, 14, 428, 148, 8, CLOUD, INK, 5)
def _body_front(p):
    p.rrect(3, 3, 447, 337, 26, SCARLET, INK, 6)
    for x0 in (66, 334): p.rect(x0, 0, x0 + 34, 337, YEL, INK, 4)
    p.ell(195, 80, 255, 140, CLOUD, INK, 5); p.ell(213, 98, 237, 122, SCARLET)
    p.ell(60, 322, 116, 372, NAVY, INK, 4); p.ell(334, 322, 390, 372, NAVY, INK, 4)
def _tag(bg, l1, l2, c2):
    def f(p):
        p.rect(0, 0, 310, 84, bg); p.text(155, 26, l1, 30, CLOUD); p.text(155, 60, l2, 32, c2)
    return f
def _plate(p):
    p.rrect(3, 3, 327, 487, 22, (248, 250, 252, 238), SCARLET, 6)

SPR = {}
def sprites():
    if SPR: return SPR
    SPR.update(bottle=mk(70, 180, _bottle), id=mk(150, 100, _idcard), med=mk(130, 110, _medkit), con=mk(190, 118, _console),
               sou=mk(130, 170, _souvenir), shoe=mk(190, 100, _shoe), chk=mk(60, 60, _check), crs=mk(60, 60, _cross),
               lid=mk(330, 170, _lid), back=mk(450, 340, _body_back), front=mk(450, 372, _body_front), plate=mk(330, 490, _plate),
               tagE=mk(310, 84, _tag(NAVY, "ESSENTIAL", "필수", SKY2)), tagN=mk(310, 84, _tag(SCARLET, "NONESSENTIAL", "불필요", WHITE)))
    SPR["front"] = SPR["front"].crop((0, 146, 450, 372))
    return SPR

def comp(cv, spr, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if alpha <= 0.004: return
    s = spr
    if abs(scale - 1) > 1e-3: s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BILINEAR)
    if rot: s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        s = s.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(cx - s.width / 2), int(cy - s.height / 2)
    X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(cv.width, x + s.width), min(cv.height, y + s.height)
    if X1 <= X0 or Y1 <= Y0: return
    cv.alpha_composite(s.crop((X0 - x, Y0 - y, X1 - x, Y1 - y)), (X0, Y0))

# ---- suitcase sorting scene: native 800x640 (suitcase left, NONESSENTIAL zone right)
ESS = [("bottle", (95, 395), (92, 318)), ("id", (232, 395), (232, 335)), ("med", (368, 395), (368, 332))]
NON = [("sou", (95, 262), (640, 215), -6), ("con", (230, 288), (640, 385), 5), ("shoe", (365, 270), (640, 512), -4)]
NSC = {"sou": 0.62, "con": 0.62, "shoe": 0.62}
DIM = {"sou": (130, 170), "con": (190, 118), "shoe": (190, 100), "bottle": (70, 180), "id": (150, 100), "med": (130, 110)}
FLY = 0.8
def scene_main(now, intro_t0, drop=True):
    S = sprites(); cv = Image.new("RGBA", (800, 640), (0, 0, 0, 0))
    pi = clamp((now - intro_t0) / 0.5); e = e_back(pi) if pi > 0 else 0
    dy = -300 * (1 - e) if drop else 0
    if pi <= 0 and drop: return cv
    comp(cv, S["plate"], 635, 345 + dy); comp(cv, S["tagN"], 635, 42 + dy); comp(cv, S["tagE"], 225, 42 + dy)
    comp(cv, S["lid"], 225, 195 + dy); comp(cv, S["back"], 225, 425 + dy)
    fl = lambda k: 4 * math.sin(now * 2.0 + k)
    def non_state(i, name, pin, pout, rot_f):
        t = TE + 0.11 * i; p = clamp((now - t) / FLY)
        wob = (math.sin(now * 38 + i) * 4 * clamp((now - (t - 0.55)) / 0.5)) if now < t else 0
        if p <= 0: return pin[0], pin[1] + dy, NSC[name], wob, False, None
        ee = e_io(p)
        x = pin[0] + (pout[0] - pin[0]) * ee
        y = pin[1] + (pout[1] - pin[1]) * ee - 230 * math.sin(math.pi * p) * (1 - 0.15 * p)
        sc = NSC[name] + (1.0 - NSC[name]) * ee
        rot = rot_f + 360 * (1 - ee) * (1 if i % 2 else -1)
        dt = now - t - FLY
        if dt > 0: y += -26 * math.exp(-dt * 4.2) * abs(math.sin(dt * 10)) + 3 * math.sin(now * 2 + i)
        return x, y + dy, sc, rot, True, dt
    def ess_state(i, name, pin, pout):
        t = TE + 0.35; p = clamp((now - t) / 0.5); ee = e_back(p)
        x = pin[0] + (pout[0] - pin[0]) * ee; y = pin[1] + (pout[1] - pin[1]) * ee
        return x, y + dy + (fl(i) if now > t + 0.5 else 0), 0.78 + 0.22 * ee, 0, False, None
    def pop(i): return clamp((now - intro_t0 - 0.35 - 0.1 * i) / 0.3)
    inside, outside, ess = [], [], []
    for i, (name, pin, pout, rf) in enumerate(NON):
        st = non_state(i, name, pin, pout, rf); (outside if st[4] else inside).append((name, st, i))
    for i, (name, pin, pout) in enumerate(ESS): ess.append((name, ess_state(i, name, pin, pout), i))
    for name, st, i in inside: comp(cv, S[name], st[0], st[1], st[2], st[3], alpha=e_out(pop(i)) if drop else 1)
    for name, st, i in ess: comp(cv, S[name], st[0], st[1], st[2], st[3], alpha=e_out(pop(3 + i)) if drop else 1)
    comp(cv, S["front"], 225, 255 + 146 + 113 + dy)
    for name, st, i in outside: comp(cv, S[name], st[0], st[1], st[2], st[3])
    for name, st, i in outside:
        dt = st[5]
        if dt is not None and dt > 0:
            bp = e_back(clamp(dt / 0.25)); w, h = DIM[name]
            comp(cv, S["crs"], st[0] + w / 2 - 14, st[1] - h / 2 + 8, 1.15 * bp)
    for name, st, i in ess:
        tt = TE + 0.95 + 0.18 * i
        if now > tt:
            bp = e_back(clamp((now - tt) / 0.25)); w, h = DIM[name]
            comp(cv, S["chk"], st[0] + w / 2 - 10, st[1] - h / 2 + 8, 1.1 * bp)
    return cv

# ---- travel scene: native 560x420
def _bez(t, A=(70, 318), C=(240, 110), B=(480, 170)):
    return ((1 - t) ** 2 * A[0] + 2 * (1 - t) * t * C[0] + t * t * B[0], (1 - t) ** 2 * A[1] + 2 * (1 - t) * t * C[1] + t * t * B[1])
TRV = {}
def _bag(p):
    p.rrect(20, 0, 70, 26, 8, None, INK, 5); p.rrect(3, 18, 87, 74, 12, SCARLET, INK, 5); p.rect(36, 18, 54, 74, YEL, INK, 3)
def _flag(p):
    p.rect(2, 0, 10, 80, INK); p.poly([(10, 4), (60, 22), (10, 42)], SCARLET, INK, 3)
def _plane(p):
    p.poly([(4, 24), (64, 4), (44, 24), (64, 44)], NAVY, WHITE, 4); p.poly([(44, 24), (64, 4), (64, 44)], SCARLET)
def _bigx(p):
    p.line([(26, 26), (154, 154)], 36, WHITE); p.line([(154, 26), (26, 154)], 36, WHITE)
    p.line([(26, 26), (154, 154)], 24, SCARLET); p.line([(154, 26), (26, 154)], 24, SCARLET)
def _maptag(p):
    p.rect(0, 0, 170, 62, NAVY); p.text(85, 33, "trips", 46, CLOUD)
def _map(p):
    p.rrect(3, 3, 557, 342, 24, CLOUD, INK, 6); p.ell(300, 220, 470, 330, SKY, None); p.ell(20, 20, 150, 150, SKY2)
    p.poly([(380, 120), (440, 40), (520, 120)], SKY2); p.ell(480, 24, 530, 74, YEL)
def travel_sprites():
    if not TRV: TRV.update(bag=mk(90, 78, _bag), flag=mk(64, 82, _flag), plane=mk(68, 48, _plane), bigx=mk(180, 180, _bigx), tag=mk(170, 62, _maptag), map=mk(560, 345, _map))
    return TRV
def scene_travel(now, t0, x_t):
    T = travel_sprites(); cv = Image.new("RGBA", (560, 420), (0, 0, 0, 0))
    pp = e_back(clamp((now - t0) / 0.35))
    if pp <= 0: return cv
    comp(cv, T["map"], 280, 62 + 172, scale=0.6 + 0.4 * pp, alpha=min(1, pp * 3))
    prog = e_io((now - t0 - 0.25) / 1.0); N = 90; n_up = int(N * prog)
    L = Image.new("RGBA", (1120, 840), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    pts = [_bez(i / N) for i in range(N + 1)]
    for i in range(0, n_up, 8):
        seg = [(x * 2, y * 2) for x, y in pts[i:min(i + 5, n_up) + 1]]
        if len(seg) > 1:
            d.line(seg, fill=SCARLET + (255,), width=18, joint="curve")
            for (x, y) in (seg[0], seg[-1]): d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=SCARLET + (255,))
    cv.alpha_composite(L.resize((560, 420), Image.LANCZOS))
    comp(cv, T["bag"], 70, 330, 1.0); comp(cv, T["flag"], 488, 150)
    pr = 0.30 * e_io((now - t0 - 0.3) / 1.3); px, py = _bez(pr); qx, qy = _bez(pr + 0.02)
    ang = -math.degrees(math.atan2(qy - py, qx - px))
    if now > t0 + 0.3: comp(cv, T["plane"], px, py + 3 * math.sin(now * 3), 1.6, ang)
    sl = e_out(clamp((now - t0 - 0.1) / 0.3)); comp(cv, T["tag"], 85 - 60 * (1 - sl), 40, alpha=sl)
    if now >= x_t:
        q = clamp((now - x_t) / 0.28); comp(cv, T["bigx"], 299, 172, scale=1 + 1.2 * (1 - e_out(q)), alpha=min(1, q * 4))
    return cv

def put_scene(img, cv, cx, top, scale, alpha=1.0):
    s = cv.resize((int(cv.width * scale), int(cv.height * scale)), Image.LANCZOS)
    if alpha < 0.999: s = s.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(s, (int(cx - s.width / 2), int(top)), s)

# ---------------------------------------------------------------- shared bits
SAFE_CX = 456
def deco(img, now, t0, cols):
    """two calm Bauhaus shapes parked in the right gutter (x>860), never behind text"""
    items = [("circle", 210, cols[0], 975, 360, 0, 6), ("tri", 190, cols[1], 960, 1010, 8, -8)]
    for i, (kind, size, col, x, y, r0, spin) in enumerate(items):
        p = clamp((now - t0 - i * 0.08) / 0.5)
        if p > 0: blit(img, shape_sprite(kind, size, col, r0 + spin * (now - t0)), x + 220 * (1 - e_out(p)), y + 8 * math.sin(now * 1.1 + i), alpha=min(1, p * 3), shake=False)
def panel(img, x0, y0, x1, y1, col, now, t0, shadow=None, dur=0.3):
    pp = e_out(clamp((now - t0) / dur)); px1 = x0 + int((x1 - x0) * pp)
    if shadow: rect(img, x0 + 12, y0 + 12, px1 + 12, y1 + 12, shadow)
    rect(img, x0, y0, px1, y1, col)
    return pp
def tchars(img, now, term, size, cy, t0, pulse=None, stagger=0.03):
    f = font(FB, size); tot = f.getlength(term); x = SAFE_CX - tot / 2
    for i, ch in enumerate(term):
        w = f.getlength(ch); lx = x + w / 2; x += w
        p = clamp((now - (t0 + stagger * i)) / 0.3)
        if p <= 0: continue
        eb = e_out(p)
        blit(img, tsprite(ch, size, "chrome", stroke=5), lx, cy + 60 * (1 - eb), alpha=min(1, p * 4), shake=False)
        if pulse is not None:
            pl = max(0.0, 1 - abs(now - (pulse + i * 0.06 + 0.1)) / 0.16)
            if pl > 0: blit(img, tsprite(ch, size, "solid", fill=YEL, stroke=5), lx, cy - 12 * pl, scale=1 + 0.1 * pl, alpha=pl, shake=False)
    return tot

# ---------------------------------------------------------------- beats
def beat_hook(img, now):
    toks = SC["beats"][0]["on_screen"].split()          # 이 단어 모르면 절대 안 됩니다!
    ts = [WT(0), WT(1), WT(2), WT(6), WT(7), WT(8)]
    band(img, 62, 296, 788, 42, now / 0.4, now)
    s1 = fit_size(toks[:3], 740, 120); r1, _ = row(toks[:3], s1, cx=SAFE_CX)
    for k, (t, x, w) in enumerate(r1):
        slam(img, now, ts[k], tsprite(t, s1, "chrome", stroke=9), x, 450, ghost=tsprite(t, s1, "ghost", fill=WHITE), p0=0.55 if ts[k] < 0.05 else 0, dur=0.2, sign=1 if k % 2 else -1)
    s2 = 250; sh = clamp((now - ts[3]) / 0.5); jx = int(10 * math.sin(now * 85) * (1 - sh)) if 0 < now - ts[3] < 0.5 else 0
    global SHX
    old = SHX; SHX += jx
    slam(img, now, ts[3], tsprite(toks[3], s2, "solid", fill=YEL, stroke=14), SAFE_CX, 665, ghost=tsprite(toks[3], s2, "ghost", fill=WHITE), dur=0.16); SHX = old
    s3 = fit_size(toks[4:], 740, 160); r3, tot3 = row(toks[4:], s3, cx=SAFE_CX, gap=0.25)
    for k, (t, x, w) in enumerate(r3):
        slam(img, now, ts[4 + k], tsprite(t, s3, "chrome", stroke=11), x, 925, ghost=tsprite(t, s3, "ghost", fill=WHITE), dur=0.16, sign=-1 if k else 1)
    pline(img, [(SAFE_CX - tot3 / 2, 1040), (SAFE_CX + tot3 / 2, 1040)], 12, SCARLET, e_io((now - ts[5]) / 0.5), outline=4)
    cx, cy, R = 190, 1215, 92
    pline(img, ellipse_pts(cx, cy, R, R), 22, SCARLET, e_io((now - ts[3]) / 0.5), outline=5)
    d = R * 0.7071; pline(img, [(cx - d, cy - d), (cx + d, cy + d)], 22, SCARLET, e_io((now - ts[4]) / 0.35), outline=5)
    deco(img, now, 0.0, (SKY, YEL))

def beat_term(img, now):
    t0 = BS["term"]; term = SC["term"]
    deco(img, now, t0, (SCARLET, SKY))
    sz = 48; fadeout = 1 - clamp((now - (WT(13) - 0.12)) / 0.12)
    rA, _ = row(["샌프란시스코", "시장이"], sz, cx=SAFE_CX); rB, _ = row(["이동을", "자제하래요."], sz, cx=SAFE_CX)
    if fadeout > 0:
        for (rr, y, idxs) in [(rA, 322, (9, 10)), (rB, 376, (11, 12))]:
            for (t, x, w), wi in zip(rr, idxs):
                if now >= WT(wi):
                    p = e_out(clamp((now - WT(wi)) / 0.25)); blit(img, tsprite(t, sz, "solid", fill=WHITE, stroke=6), x + (-70 if wi % 2 else 70) * (1 - p), y, alpha=p * fadeout, shake=False)
    if now >= WT(13):
        r, _ = row(["그", "단어가"], 64, cx=SAFE_CX, gap=0.3)
        for (t, x, w), wi in zip(r, (13, 14)): slam(img, now, WT(wi), tsprite(t, 64, "solid", fill=YEL, stroke=7), x, 350, dur=0.18)
    panel(img, 62, 424, 850, 562, BLK, now, t0, shadow=YEL)
    s = fit_size([term], 720, 112); tot = tchars(img, now, term, s, 484, t0, pulse=TE)
    x0 = SAFE_CX - tot / 2
    pline(img, [(x0, 548), (x0 + tot, 548)], 8, YEL, e_io((now - TE) / 0.5))
    put_scene(img, scene_main(now, t0 + 0.05), SAFE_CX, 600, 0.9)

def beat_meaning(img, now):
    t0 = BS["meaning"]; term = SC["term"]
    deco(img, now, t0, (SKY, SCARLET))
    f = font(FB, 52); cw = int(f.getlength(term)) + 56
    rect(img, 62, 304, 62 + cw, 372, BLK); blit(img, tsprite(term, 52, "chrome", stroke=4), 62 + 28 + f.getlength(term) / 2, 340, shake=False)
    panel(img, 62, 396, 850, 560, YEL, now, t0, shadow=BLK)
    toks = ["꼭", "필요하지", "않은"]; s1 = fit_size(toks, 700, 100); r1, tot = row(toks, s1, cx=SAFE_CX - 6, gap=0.2)
    for k, (t, x, w) in enumerate(r1):
        slam(img, now, WT(16 + k), tsprite(t, s1, "solid", fill=BLK), x, 478, dur=0.2, sign=1 if k else -1)
    ux0 = r1[2][1] - r1[2][2] / 2; ux1 = r1[2][1] + r1[2][2] / 2
    pline(img, [(ux0, 540), (ux1, 540)], 9, SCARLET, e_io((now - WT(18) - 0.2) / 0.4))
    sp = e_io((now - t0 - 0.3) / 0.35)
    if sp > 0: rect(img, 640, 560, 700, 560 + int(46 * sp), YEL)
    put_scene(img, scene_main(now, t0, drop=False), SAFE_CX, 600, 0.9)
    q = e_io((now - WT(18)) / 0.4)
    if q > 0:
        x0 = 96 + 0.9 * 470; y0 = 600 + 0.9 * 100; x1 = 96 + 0.9 * 800; y1 = 600 + 0.9 * 590
        pline(img, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 8, YEL, q, closed=True, outline=3)

def beat_example_en(img, now):
    t0 = BS["example_en"]; ex = SC["beats"][3]["on_screen"].split()
    deco(img, now, t0, (YEL, SCARLET))
    pw = e_out(clamp((now - t0) / 0.3))
    rect(img, 62, 312, 62 + int(788 * pw), 744, NAVY, 0.95)
    slide(img, now, t0 + 0.1, tsprite("예문", 44, "solid", fill=WHITE), 62 + 70, 346, -60, 0.25)
    S = 84; lx = 100
    r1, _ = row(ex[:2], S, x0=lx, fnt=FBOLD)
    for k, (t, x, w) in enumerate(r1): slide(img, now, WT(21 + k), tsprite(t, S, "solid", fill=CLOUD, fnt=FBOLD), x, 430, -110 if k else 110)
    hs = fit_size([ex[2]], 640, 96); hw = font(FB, hs).getlength(ex[2]); bx0, by0 = 88, 486; bx1, by1 = bx0 + hw + 44, by0 + 128
    pline(img, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)], 6, YEL, e_io((now - t0 - 0.3) / 0.6), closed=True)
    th = WT(23) - 0.05
    if now >= th:
        pw2 = e_out(clamp((now - th) / 0.22)); rect(img, bx0, by0, bx0 + int((bx1 - bx0) * pw2), by1, YEL)
        slam(img, now, WT(23), tsprite(ex[2], hs, "solid", fill=BLK), bx0 + 22 + hw / 2, by0 + 66, dur=0.16)
    r3, _ = row(ex[3:], S, x0=lx, fnt=FBOLD)
    for k, (t, x, w) in enumerate(r3): slide(img, now, WT(24 + k), tsprite(t, S, "solid", fill=CLOUD, fnt=FBOLD), x, 668, 110 if k % 2 else -110)
    put_scene(img, scene_travel(now, t0 + 0.05, WT(24)), SAFE_CX, 768, 0.95)

def beat_example_ko(img, now):
    t0 = BS["example_ko"]; ko = SC["beats"][4]["on_screen"].split()
    deco(img, now, t0, (SKY, YEL))
    pw = e_out(clamp((now - t0) / 0.3))
    rect(img, 62, 312, 62 + int(788 * pw), 744, NAVY, 0.95); rect(img, 62, 312, 62 + int(24 * pw), 744, YEL)
    slide(img, now, t0 + 0.1, tsprite("해석", 46, "solid", fill=WHITE), 62 + 90, 350, -60, 0.25)
    S = fit_size(["외출을", "피해", "주세요."], 640, 86, gap=0.3, fnt=FBOLD); lx = 116
    r1, _ = row(ko[:2], S, x0=lx, fnt=FBOLD)
    for k, (t, x, w) in enumerate(r1): slide(img, now, WT(27 + k), tsprite(t, S, "solid", fill=CLOUD, fnt=FBOLD), x, 430, -100)
    hw = font(FB, S).getlength(ko[2]); hx0, hy0 = 100, 486; hx1, hy1 = hx0 + hw + 40, hy0 + 124
    th = WT(29) - 0.05
    if now >= th:
        pw2 = e_out(clamp((now - th) / 0.22)); rect(img, hx0, hy0, hx0 + int((hx1 - hx0) * pw2), hy1, YEL)
        slam(img, now, WT(29), tsprite(ko[2], S, "solid", fill=BLK), hx0 + 20 + hw / 2, hy0 + 64, dur=0.16)
    r3, _ = row(ko[3:], S, x0=lx, fnt=FBOLD)
    for k, (t, x, w) in enumerate(r3): slide(img, now, WT(30 + k), tsprite(t, S, "solid", fill=CLOUD, fnt=FBOLD), x, 668, 100 if k % 2 else -100)
    put_scene(img, scene_travel(now, BS["example_en"] + 0.05, WT(24)), SAFE_CX, 768, 0.95)

def bookmark_pts(x, y, w, h):
    return [(x, y + h), (x, y), (x + w, y), (x + w, y + h), (x + w / 2, y + h - h * 0.24), (x, y + h)]

def beat_payoff(img, now):
    t0 = BS["payoff"]; term = SC["term"]
    deco(img, now, t0, (SCARLET, SKY))
    on = EXPR_S <= now <= EXPR_E
    panel(img, 62, 310, 850, 486, YEL if on else BLK, now, t0, shadow=(BLK if on else YEL), dur=0.2)
    s = fit_size([term], 720, 124)
    p = e_out(clamp((now - t0) / 0.2)); sp = tsprite(term, s, "solid", fill=BLK) if on else tsprite(term, s, "chrome", stroke=5)
    blit(img, sp, SAFE_CX, 400, scale=1 + 0.25 * (1 - p), alpha=min(1, p * 4), shake=False)
    bump = max(0.0, 1 - (now - EXPR_S) / 0.35) if now >= EXPR_S else 0
    put_scene(img, scene_main(now, t0, drop=False), SAFE_CX, 522 - int(14 * bump), 0.62)
    if now >= SAVE_S:
        q = clamp((now - SAVE_S) / 0.3); e = e_back(q); wob = 1 + 0.02 * math.sin((now - SAVE_S) * 9) * (now - SAVE_S < 1)
        L = Image.new("RGBA", (788, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        d.rectangle((12, 12, 787, 149), fill=BLK + (255,)); d.rectangle((0, 0, 775, 137), fill=YEL + (255,))
        d.polygon(bookmark_pts(40, 22, 62, 96), fill=BLK + (255,))
        spr = tsprite("저장해 두기", 88, "solid", fill=BLK)
        L.alpha_composite(spr, (128, max(0, (137 - spr.height) // 2 + 4)))
        if e > 0.02:
            s2 = L.resize((max(1, int(L.width * e * wob)), max(1, int(L.height * e * wob))), Image.LANCZOS)
            img.paste(s2, (int(SAFE_CX - s2.width / 2 - 6), int(1030 - s2.height / 2)), s2)

BEAT_FN = [beat_hook, beat_term, beat_meaning, beat_example_en, beat_example_ko, beat_payoff]

# ---------------------------------------------------------------- persistent chrome
def make_pill():
    f = font(FB, 34); t = "NEWS ENGLISH · CNN"; w = int(f.getlength(t))
    im = Image.new("RGBA", (w + 150, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width - 1, 63), fill=BLK); d.ellipse((12, 12, 52, 52), fill=YEL); d.rectangle((im.width - 46, 14, im.width - 14, 46), fill=SCARLET)
    d.polygon([(70, 52), (70, 12), (100, 52)], fill=SKY) if False else None
    d.text((68, 8), t, font=f, fill=WHITE)
    return im
PILL = make_pill()
def make_handle():
    f = font(FBOLD, 36); t = "지나쌤영어  @jina.ssam_english"; w = int(f.getlength(t))
    im = Image.new("RGBA", (w + 60, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, 63), 32, fill=INK + (225,)); d.text((30, 8), t, font=f, fill=WHITE)
    return im
HANDLE = make_handle()

import bird as BIRD
def mouth_env(total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", MP3, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64); spf = 8000 / FPS; n = int(len(x) / spf)
    rms = np.array([np.sqrt(np.mean(x[int(i * spf):int((i + 1) * spf)] ** 2)) for i in range(n)])
    v = np.clip(rms / (np.percentile(rms, 90) or 1), 0, 1) ** 0.8; v[v < 0.08] = 0
    env = np.zeros(int(round(total * FPS)) + 2); prev = 0.0
    for i in range(len(env)):
        tgt = v[i] if i < n else 0.0; prev = tgt if tgt >= prev else prev * 0.6
        if prev < 0.02: prev = 0.0
        env[i] = prev
    return env

def render_frame(now, mouth):
    global SHX, SHY
    img = Image.fromarray(make_bg(now), "RGB")
    SHX = SHY = 0
    bi = beat_index(now); tcut = CUTS[bi]
    BEAT_FN[bi](img, now)
    img.paste(PILL, (62, 226), PILL)
    since = now - tcut; bob = -10 * math.exp(-since * 9) * abs(math.cos(since * 14)) if since >= 0 else 0
    sp = BIRD.sprite(mouth); bx = int(735 - sp.width / 2); by = int(1430 - sp.height + bob + 3 * math.sin(now * 2.2))
    sh = Image.new("RGBA", (sp.width, 30), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((10, 4, sp.width - 10, 26), fill=(10, 4, 30, 150))
    img.paste(sh, (bx, 1417), sh); img.paste(sp, (bx, by), sp)
    img.paste(HANDLE, ((W - HANDLE.width) // 2, 1588), HANDLE)
    return img

def contrast_report():
    navy_over = lambda base, a=0.93: tuple(int(NAVY[i] * a + base[i] * (1 - a)) for i in range(3))
    rows = [("hook chrome white vs stroke INK", contrast(WHITE, INK)), ("hook chrome pink end vs INK", contrast((255, 160, 228), INK)),
            ("hook yellow vs INK stroke", contrast(YEL, INK)), ("hook scarlet ring vs white outline", contrast(SCARLET, WHITE)),
            ("term chrome vs black panel", contrast((255, 160, 228), BLK)), ("term white ctx text vs INK stroke", contrast(WHITE, INK)),
            ("meaning black on yellow", contrast(BLK, YEL)), ("example cloud on navy panel (0.95 over magenta worst)", contrast(CLOUD, navy_over((255, 60, 190), 0.95))),
            ("example cloud on navy panel (over sun yellow worst)", contrast(CLOUD, navy_over((255, 225, 90), 0.95))),
            ("example/ko highlight black on yellow", contrast(BLK, YEL)), ("payoff black on yellow (expr + save)", contrast(BLK, YEL)),
            ("tag ESSENTIAL cloud on navy", contrast(CLOUD, NAVY)), ("tag 필수 sky2 on navy", contrast(SKY2, NAVY)), ("tag NONESSENTIAL white on scarlet", contrast(WHITE, SCARLET)),
            ("trips tag cloud on navy", contrast(CLOUD, NAVY)), ("check navy on sky badge (graphic)", contrast(INK, SKY)), ("X white on scarlet badge (graphic)", contrast(WHITE, SCARLET)),
            ("handle white on INK", contrast(WHITE, INK)), ("pill white on black", contrast(WHITE, BLK))]
    for n, c in rows: print(f"  contrast {c:5.2f}  {n}")

def main():
    if "--frames" in sys.argv:
        os.makedirs(FR, exist_ok=True); ts = [float(a) for a in sys.argv[sys.argv.index("--frames") + 1:]]
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
        env = mouth_env(dur + TAIL)
        for t in ts: render_frame(t, env[min(int(t * FPS), len(env) - 1)]).save(f"{FR}/kw3_{RID}_t{t:05.2f}.png")
        return
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
    total = round((dur + TAIL) * FPS) / FPS; nfr = int(round(total * FPS)); env = mouth_env(total)
    os.makedirs(FR, exist_ok=True); out = f"{OUT}/kw3_{RID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", MP3,
           "-filter_complex", "[1:a]apad,aformat=channel_layouts=stereo[a]", "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "1", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-t", f"{total:.3f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(nfr): p.stdin.write(render_frame(i / FPS, env[i]).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg failed")
    print("done", out, total); contrast_report()

if __name__ == "__main__":
    main()
