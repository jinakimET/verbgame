#!/usr/bin/env python3
"""kw3_11 ("nonessential"): BAUHAUS + VAPORWAVE + LINE ANIMATION + kinetic typography.
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
        v = 120 + 135 * (0.5 + 0.5 * math.sin(now * 3 + ph0))
        top[sy - 1:sy + 2, sx - 1:sx + 2] = (v, v, v)
        if k == 2: top[sy, sx - 5:sx + 6] = (v, v, v); top[sy - 5:sy + 6, sx] = (v, v, v)
    fr[:HOR] = top
    # floor: horizontal lines flow toward the viewer
    d = b["d"]; s = 420.0 / d - now * 0.9
    dist = np.minimum(s % 1, 1 - (s % 1)) * d * d / 420.0
    th = 1.5 + d * 0.008
    ha = (np.clip(1 - dist / th, 0, 1) + np.clip(1 - dist / (th * 4.5), 0, 1) ** 2 * 0.4) * np.clip(d / 100, 0, 1) ** 1.5
    fl = b["fl"] + b["vcol"] + ha[..., None] * np.array(MAG, np.float64)[None, None, :]
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
WT = lambda i: WORDS[i]["s"]
CUTS = [b["start"] for b in BEATS]
HITS = [(WT(6), 16), (WT(8), 11)] + [(t, 7) for t in CUTS[1:]]
def shake_at(now):
    sx = sy = 0.0
    for t, a in HITS:
        dt = now - t
        if 0 <= dt < 0.45:
            k = a * math.exp(-dt * 11); sx += k * math.cos(dt * 70); sy += k * 0.7 * math.sin(dt * 83)
    return int(sx), int(sy)

def beat_index(now):
    i = 0
    for k, t in enumerate(CUTS):
        if now >= t - 1e-6: i = k
    return i

# ---------------------------------------------------------------- beats
SAFE_CX = 456
def beat_hook(img, now):
    t0 = 0.0
    draw_shapes(img, now, t0, [("tri", 300, SCARLET, 70, 1010, 10, 40, -250, 0), ("square", 190, SKY, 960, 1060, 20, -55, 250, 0),
                              ("half", 260, YEL, 930, 330, 0, 25, 0, -300), ("bar", (560, 46), BLK, 150, 255, -18, 0, -400, 0)])
    band(img, 62, 306, 788, 50, now / 0.45, now); band(img, 62, 1086, 788, 50, (now - 0.1) / 0.45, now)
    toks = SC["beats"][0]["on_screen"].split()          # 이 단어 모르면 절대 안 돼요!
    ts = [WT(0), WT(1), WT(2), WT(6), WT(7), WT(8)]
    # forbidden sign: circle strokes in on 절대, slash on 안 됩니다
    cx, cy, R = SAFE_CX, 722, 338
    pline(img, ellipse_pts(cx, cy, R, R), 30, SCARLET, e_io((now - ts[3]) / 0.6), outline=6)
    d = R * 0.7071
    pline(img, [(cx - d, cy - d), (cx + d, cy + d)], 30, SCARLET, e_io((now - ts[4]) / 0.45), outline=6)
    s1 = fit_size(toks[:3], 720, 126); r1, _ = row(toks[:3], s1, cx=SAFE_CX)
    for k, (t, x, w) in enumerate(r1):
        sp = tsprite(t, s1, "chrome", stroke=9); gh = tsprite(t, s1, "ghost", fill=WHITE)
        slam(img, now, ts[k], sp, x, 452 + 4 * math.sin(now * 3 + k) * (now > ts[k] + 0.3), ghost=gh, p0=0.55 if ts[k] < 0.05 else 0, sign=1 if k % 2 else -1)
    s2 = 300; sp = tsprite(toks[3], s2, "solid", fill=YEL, stroke=16); gh = tsprite(toks[3], s2, "ghost", fill=WHITE)
    sh = clamp((now - ts[3]) / 0.6); jx = int(16 * math.sin(now * 85) * (1 - sh)) if 0 < now - ts[3] < 0.6 else 0
    global SHX
    old = SHX; SHX += jx; slam(img, now, ts[3], sp, SAFE_CX, 712, ghost=gh, dur=0.16); SHX = old
    s3 = fit_size(toks[4:], 740, 200); r3, _ = row(toks[4:], s3, cx=SAFE_CX, gap=0.25)
    for k, (t, x, w) in enumerate(r3):
        sp = tsprite(t, s3, "chrome", stroke=12); gh = tsprite(t, s3, "ghost", fill=WHITE)
        slam(img, now, ts[4 + k], sp, x, 940, ghost=gh, dur=0.16, sign=-1 if k else 1)

def beat_term(img, now):
    t0 = BS["term"]; term = SC["term"]
    draw_shapes(img, now, t0, [("circle", 340, SCARLET, 830, 430, 0, 0, 300, -100), ("tri", 300, SKY, 110, 1060, -10, -35, -300, 100),
                              ("square", 150, YEL, 905, 1010, 15, 50, 300, 0), ("bar", (520, 40), BLK, 650, 1020, -22, 0, 0, 300)])
    # animated connecting lines
    pline(img, [(830, 600), (850, 560), (850, 520)], 5, WHITE, e_io((now - t0 - 0.3) / 0.5))
    pline(img, [(120, 940), (120, 880), (62, 880)], 5, WHITE, e_io((now - t0 - 0.9) / 0.5))
    # context words (spoken order)
    for (tk, wi, y, x0) in [("샌프란시스코", 9, 410, None), ("시장이", 10, 410, None), ("이동을", 11, 490, None), ("자제하래요", 12, 490, None)]:
        pass
    sz = 60
    rA, _ = row(["샌프란시스코", "시장이"], sz, cx=SAFE_CX - 20); rB, _ = row(["이동을", "자제하래요"], sz, cx=SAFE_CX - 20)
    for (rr, y, idxs) in [(rA, 408, (9, 10)), (rB, 486, (11, 12))]:
        for (t, x, w), wi in zip(rr, idxs):
            slide(img, now, WT(wi), tsprite(t, sz, "solid", fill=WHITE, stroke=7), x, y, -90 if wi % 2 else 90)
    # panel: black block + yellow offset shadow
    pp = e_out(clamp((now - t0) / 0.3)); px1 = 62 + int(788 * pp)
    rect(img, 76, 626, px1 + 14, 868, YEL); rect(img, 62, 612, px1, 854, BLK)
    s = fit_size([term], 720, 140, fnt=FB); f = font(FB, s); tot = f.getlength(term); x = SAFE_CX - tot / 2 - 5
    cyc = 730
    ul_l, ul_r = x, x + tot
    for i, ch in enumerate(term):
        w = f.getlength(ch); lx = x + w / 2; x += w
        ts = t0 + 0.05 * i; p = clamp((now - ts) / 0.42)
        if p <= 0: continue
        eb = e_back(p); sgn = 1 if i % 2 == 0 else -1
        spr = tsprite(ch, s, "chrome", stroke=5)
        blit(img, spr, lx + sgn * -620 * (1 - eb), cyc + (-90 * sgn) * (1 - eb), rot=sgn * 35 * (1 - eb), alpha=min(1, p * 4))
        pulse = max(0.0, 1 - abs(now - (WT(15) + i * 0.06 + 0.1)) / 0.16)
        if pulse > 0:
            blit(img, tsprite(ch, s, "solid", fill=YEL, stroke=5), lx, cyc - 16 * pulse, scale=1 + 0.14 * pulse, alpha=pulse)
    pline(img, [(ul_l, 800), (ul_r, 800)], 14, YEL, e_io((now - t0 - 1.0) / 0.6))
    pline(img, zigzag(ul_l, ul_r, 826, 7, 24), 6, CYAN, e_io((now - WT(15)) / 0.7))
    # "그 단어가" pointing up at the term
    for (t, wi, xx) in [("그", 13, 150), ("단어가", 14, 300)]:
        slam(img, now, WT(wi), tsprite(t, 78, "solid", fill=YEL, stroke=8), xx, 960, dur=0.18)
    pline(img, [(380, 940), (470, 905), (470, 875), (450, 892)], 7, YEL, e_io((now - WT(14) - 0.1) / 0.35))

def beat_meaning(img, now):
    t0 = BS["meaning"]; term = SC["term"]
    draw_shapes(img, now, t0, [("circle", 300, SKY, 800, 1100, 0, 0, 300, 200), ("tri", 270, SCARLET, 120, 340, 0, 50, -250, -100),
                              ("half", 250, YEL, 925, 330, 180, -20, 300, 0), ("bar", (40, 420), BLK, 880, 760, 0, 0, 300, 0)])
    # term chip with "non" circled (line animation)
    s = 80; f = font(FB, s); tot = f.getlength(term); x0 = SAFE_CX - tot / 2
    chip_y = 470
    slide(img, now, t0, tsprite(term, s, "chrome", stroke=7), SAFE_CX, chip_y, 0, 0.01)
    wn = f.getlength("non")
    pline(img, ellipse_pts(x0 + wn / 2 - 6, chip_y + 4, wn / 2 + 4, 62, -90), 9, SCARLET, e_io((now - WT(18)) / 0.5), outline=4)
    pline(img, [(x0 + wn + 6, chip_y + 66), (x0 + tot, chip_y + 66)], 7, CYAN, e_io((now - WT(18) - 0.45) / 0.45))
    # yellow block
    pp = e_out(clamp((now - t0) / 0.3)); bx1 = 62 + int(788 * pp)
    rect(img, 76, 626, bx1 + 14, 1024, BLK); rect(img, 62, 612, bx1, 1010, YEL)
    toks1 = ["꼭", "필요하지"]; s1 = fit_size(toks1, 680, 150)
    r1, _ = row(toks1, s1, x0=108)
    for k, (t, x, w) in enumerate(r1):
        slam(img, now, WT(16 + k), tsprite(t, s1, "solid", fill=BLK), x, 730, dur=0.2, sign=1 if k else -1)
    slam(img, now, WT(18), tsprite("않은", s1, "solid", fill=SCARLET if False else BLK), 108 + font(FB, s1).getlength("않은") / 2, 890, dur=0.2)
    pline(img, [(108, 985), (108 + font(FB, s1).getlength("않은") + 40, 985)], 11, SCARLET, e_io((now - WT(18) - 0.3) / 0.5))

def beat_example_en(img, now):
    t0 = BS["example_en"]; ex = SC["beats"][3]["on_screen"].split()    # Please avoid nonessential trips this week.
    draw_shapes(img, now, t0, [("circle", 320, YEL, 90, 340, 0, 0, -300, 0), ("tri", 270, SCARLET, 900, 400, 0, -45, 300, -100),
                              ("square", 200, SKY, 850, 1090, 10, 40, 300, 100), ("bar", (500, 42), BLK, 230, 1090, 8, 0, -400, 0)])
    pw = e_out(clamp((now - t0) / 0.3))
    ImageDraw.Draw(img)  # noqa
    rect(img, 62, 496, 62 + int(788 * pw), 1046, NAVY, 0.93)
    pline(img, [(62, 496), (850, 496), (850, 1046), (62, 1046)], 7, MAG, e_io((now - t0) / 0.9), closed=True)
    # chip
    slide(img, now, t0 + 0.1, tsprite("예문", 44, "solid", fill=WHITE), 62 + 70, 556, -60, 0.25)
    rect(img, 62, 530, 62 + 140, 582, SCARLET, 0.0)
    # line 1
    S = 88; lx = 104
    r1, _ = row(ex[:2], S, x0=lx)
    for k, (t, x, w) in enumerate(r1):
        slide(img, now, WT(21 + k), tsprite(t, S, "solid", fill=CLOUD, stroke=0, fnt=FBOLD), x, 676, -110 if k else 110)
    # highlight box line: dashed-line frame draws first, fills on the word
    hs = 96; hw = font(FB, hs).getlength(ex[2]); bx0, by0 = 90, 756; bx1, by1 = bx0 + hw + 44, by0 + 136
    pline(img, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)], 6, YEL, e_io((now - t0 - 0.35) / 0.6), closed=True)
    th = WT(23) - 0.05
    if now >= th:
        pw2 = e_out(clamp((now - th) / 0.22)); rect(img, bx0, by0, bx0 + int((bx1 - bx0) * pw2), by1, YEL)
        slam(img, now, WT(23), tsprite(ex[2], hs, "solid", fill=BLK), bx0 + 22 + hw / 2, by0 + 68, dur=0.16)
    r3, _ = row(ex[3:], S, x0=lx)
    for k, (t, x, w) in enumerate(r3):
        slide(img, now, WT(24 + k), tsprite(t, S, "solid", fill=CLOUD, fnt=FBOLD), x, 960, 110 if k % 2 else -110)

def beat_example_ko(img, now):
    t0 = BS["example_ko"]; ko = SC["beats"][4]["on_screen"].split(); en = SC["beats"][3]["on_screen"]
    draw_shapes(img, now, t0, [("circle", 360, SKY, 70, 1000, 0, 0, -300, 100), ("square", 210, SCARLET, 880, 380, 12, 35, 300, -100),
                              ("tri", 250, YEL, 905, 1060, 0, -40, 300, 100), ("bar", (46, 520), BLK, 40, 520, 0, 0, -200, 0)])
    pw = e_out(clamp((now - t0) / 0.3))
    rect(img, 62, 470, 62 + int(788 * pw), 1030, NAVY, 0.93)
    rect(img, 62, 470, 62 + int(24 * pw), 1030, YEL)
    slide(img, now, t0 + 0.1, tsprite("해석", 46, "solid", fill=WHITE), 62 + 90, 534, -60, 0.25)
    S = fit_size(["이번", "주에는", "불필요한"], 640, 80)
    r1, _ = row(ko[:3], S, x0=116)
    ts = [WT(27), WT(28), WT(29)]
    hlw = r1[2][2]; hx0 = r1[2][1] - hlw / 2 - 16
    for k, (t, x, w) in enumerate(r1[:2]):
        slide(img, now, ts[k], tsprite(t, S, "solid", fill=CLOUD, fnt=FBOLD), x, 664, -100)
    th = ts[2] - 0.05
    if now >= th:
        pw2 = e_out(clamp((now - th) / 0.22)); rect(img, hx0, 618, hx0 + int((hlw + 32) * pw2), 618 + int(S * 1.5), YEL)
        slam(img, now, ts[2], tsprite(ko[2], S, "solid", fill=BLK), r1[2][1], 664, dur=0.16)
    r2, _ = row(ko[3:], S, x0=116)
    for k, (t, x, w) in enumerate(r2):
        slide(img, now, WT(30 + k), tsprite(t, S, "solid", fill=CLOUD, fnt=FBOLD), x, 790, 100 if k % 2 else -100)
    pline(img, [(116, 880), (820, 880)], 4, MAG, e_io((now - t0 - 0.5) / 0.6))
    pline(img, [(hx0, 618 + int(S * 1.5) + 12), (hx0 + hlw + 32, 618 + int(S * 1.5) + 12)], 8, SCARLET, e_io((now - th - 0.1) / 0.4))
    e1, e2 = "Please avoid nonessential", "trips this week."
    for k, (tx, y) in enumerate([(e1, 925), (e2, 972)]):
        slide(img, now, t0 + 0.7 + 0.15 * k, tsprite(tx, 40, "solid", fill=DIMKO, fnt=FBOLD), 116 + font(FBOLD, 40).getlength(tx) / 2, y, 0, 0.3)

def bookmark_pts(x, y, w, h):
    return [(x, y + h), (x, y), (x + w, y), (x + w, y + h), (x + w / 2, y + h - h * 0.24), (x, y + h)]

def beat_payoff(img, now):
    t0 = BS["payoff"]; term = SC["term"]
    draw_shapes(img, now, t0, [("circle", 330, SCARLET, 800, 420, 0, 0, 300, -200), ("tri", 260, SKY, 110, 1090, 0, 30, -300, 100),
                              ("square", 180, YEL, 900, 1000, 18, -45, 300, 0), ("bar", (480, 40), BLK, 720, 1230, -14, 0, 500, 0)])
    bx, by, bw, bh = 96, 520, 190, 330
    prog = e_io((now - t0) / 0.7)
    if now - t0 > 0.7:
        fa = clamp((now - t0 - 0.7) / 0.25); ptsf = bookmark_pts(bx, by, bw, bh)
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(im).polygon(ptsf, fill=YEL + (int(255 * fa),))
        img.paste(im.crop((bx - 4, by - 4, bx + bw + 4, by + bh + 4)), (bx - 4 + SHX, by - 4 + SHY), im.crop((bx - 4, by - 4, bx + bw + 4, by + bh + 4)))
    pline(img, bookmark_pts(bx, by, bw, bh), 18, WHITE if now - t0 < 0.7 else NAVY, prog, outline=0)
    toks = SC["beats"][5]["on_screen"].split()      # 저장해 두기
    S = 150
    for k, tk in enumerate(toks):
        slam(img, now, WT(33 + k) if k == 0 else WT(34), tsprite(tk, S, "chrome", stroke=11), 560 + (0 if k == 0 else 20), 600 + k * 190, dur=0.2, sign=1 if k else -1)
    # yellow bauhaus block with the term
    hs = 82; hw = font(FB, hs).getlength(term); bx0 = 90; by0 = 960
    pp = e_out(clamp((now - t0 - 0.5) / 0.3)); rect(img, bx0 + 12, by0 + 12, bx0 + 12 + int((hw + 56) * pp), by0 + 142, BLK); rect(img, bx0, by0, bx0 + int((hw + 56) * pp), by0 + 130, YEL)
    if pp > 0.95: blit(img, tsprite(term, hs, "solid", fill=BLK), bx0 + 28 + hw / 2, by0 + 66)
    pline(img, zigzag(bx0, bx0 + hw + 56, by0 + 168, 7, 26), 6, CYAN, e_io((now - t0 - 0.9) / 0.6))

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
    arr = make_bg(now)
    bi = beat_index(now); tcut = CUTS[bi]
    fl = 0.38 * max(0.0, 1 - (now - tcut) / 0.14) if bi > 0 else 0.0
    if fl > 0: arr = (arr * (1 - fl) + 255 * fl).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    SHX, SHY = shake_at(now)
    BEAT_FN[bi](img, now)
    SHX = SHY = 0
    img.paste(PILL, (62, 226), PILL)
    # bird in front of the sun, bounces on cuts
    since = now - tcut; bob = -22 * math.exp(-since * 9) * abs(math.cos(since * 14)) if since >= 0 else 0
    sp = BIRD.sprite(mouth); bx = int(450 - sp.width / 2); by = int(1385 - sp.height + bob + 4 * math.sin(now * 2.2))
    sh = Image.new("RGBA", (sp.width, 30), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((10, 4, sp.width - 10, 26), fill=(10, 4, 30, 150))
    img.paste(sh, (bx, 1372), sh); img.paste(sp, (bx, by), sp)
    img.paste(HANDLE, ((W - HANDLE.width) // 2, 1588), HANDLE)
    return img

def contrast_report():
    navy_over = lambda base, a=0.93: tuple(int(NAVY[i] * a + base[i] * (1 - a)) for i in range(3))
    rows = [("hook chrome white vs stroke INK", contrast(WHITE, INK)), ("hook chrome pink end vs INK", contrast((255, 160, 228), INK)),
            ("hook 절대 yellow vs INK stroke", contrast(YEL, INK)), ("hook slash/circle scarlet vs white outline", contrast(SCARLET, WHITE)),
            ("term chrome vs black panel", contrast((255, 160, 228), BLK)), ("term white ctx text vs INK stroke", contrast(WHITE, INK)),
            ("meaning black on yellow", contrast(BLK, YEL)), ("example cloud on navy panel (over magenta worst)", contrast(CLOUD, navy_over((255, 60, 190)))),
            ("example cloud on navy panel (over sun yellow worst)", contrast(CLOUD, navy_over((255, 225, 90)))),
            ("example highlight black on yellow", contrast(BLK, YEL)), ("ko dim english C4D4E2 on navy panel worst", contrast(DIMKO, navy_over((255, 60, 190)))),
            ("handle white on INK", contrast(WHITE, INK)), ("pill white on black", contrast(WHITE, BLK)), ("chip white on scarlet", contrast(WHITE, SCARLET))]
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
