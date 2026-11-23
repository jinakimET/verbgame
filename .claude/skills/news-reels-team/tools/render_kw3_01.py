#!/usr/bin/env python3
"""kw3_01 'fail to agree on' - NEO-BRUTALISM + KINETIC TYPOGRAPHY + SHAPE MORPH.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-23-cnn python3 render_kw3_01.py"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird as BIRD

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-23-cnn")
RID = "01"
OUT = f"{ROOT}/06_keyword_reels/v3"; FR = f"{OUT}/frames"
MP3 = f"{ROOT}/audio/v3/kw3_{RID}.mp3"
W, H, FPS, TAIL = 1080, 1920, 30, 0.7
BLACK_F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
BOLD_F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def hx(s): s = s.lstrip("#"); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
INK, AZURE, VERM, OFF = hx("080F1B"), hx("329DD2"), hx("FF4C2B"), hx("F4F8FB")
YEL = hx("FFD84D"); BLK = (0, 0, 0); BG1 = hx("0E1A2E")
_fc = {}
def font(size, path=BLACK_F):
    k = (size, path)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size, index=1)
    return _fc[k]
def lum(c):
    f = lambda v: (v/255/12.92) if v/255 <= .03928 else ((v/255+.055)/1.055) ** 2.4
    return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

# ---------- data ----------
WK = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[RID]
words = WK["words"]; BT = [b["start"] for b in WK["beats"]]
def ws(i): return words[i]["s"]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3],
                           capture_output=True, text=True).stdout)
TOTAL = round((dur + TAIL) * FPS) / FPS
SHAPE_COL = [AZURE, VERM, YEL, AZURE, VERM, AZURE]
PLAT_COL = [YEL, OFF, AZURE, YEL, OFF, VERM]

# ---------- stickers ----------
def ease_back(p, c1=1.70158):
    q = p - 1; return 1 + (c1 + 1) * q ** 3 + c1 * q ** 2
class Sticker:
    """2x supersampled brutalist block (thick outline + hard offset shadow), optional rotation."""
    def __init__(s, w, h, bg=None, lines=(), size=0, fg=INK, ol=8, sh=12, angle=0.0, circle=False, fpath=BLACK_F, lh=1.18, align="c"):
        s.angle = angle; k = 2; pad = ol + sh + 4
        im = Image.new("RGBA", ((w + 2 * pad) * k, (h + 2 * pad) * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        box = (pad * k, pad * k, (pad + w) * k, (pad + h) * k)
        if bg is not None:
            sb = tuple(v + sh * k for v in box)
            if circle: d.ellipse(sb, fill=BLK); d.ellipse(tuple(b - ol * k for b in box[:2]) + tuple(b + ol * k for b in box[2:]), fill=BLK); d.ellipse(box, fill=bg)
            else:
                ob = (box[0] - ol * k, box[1] - ol * k, box[2] + ol * k, box[3] + ol * k)
                d.rectangle(tuple(v + sh * k for v in ob), fill=BLK); d.rectangle(ob, fill=BLK); d.rectangle(box, fill=bg)
        if lines:
            f = font(size * k, fpath); n = len(lines); tot = n * size * lh
            for i, ln in enumerate(lines):
                cy = (pad + h / 2 - tot / 2 + size * lh * (i + .5)) * k
                d.text(((pad + w / 2) * k, cy), ln, font=f, fill=fg + (255,), anchor="mm")
        s.src = im; s.w, s.h, s.pad = w, h, pad; s._c = {}
    def get(s, sc=1.0, extra=0.0):
        key = (round(sc, 2), round(extra, 1))
        if key in s._c: return s._c[key]
        r = s.src.rotate(s.angle + extra, resample=Image.BICUBIC, expand=True)
        out = r.resize((max(1, int(r.width * sc / 2)), max(1, int(r.height * sc / 2))), Image.LANCZOS)
        if len(s._c) < 400: s._c[key] = out
        return out
def measure(text, size, fpath=BLACK_F):
    return font(size, fpath).getlength(text)
def block(text, size, fg, bg, angle=0, padx=34, pady=18, **kw):
    w = int(measure(text, size)) + 2 * padx; h = int(size * 1.18) + 2 * pady
    return Sticker(w, h, bg, [text], size, fg, angle=angle, **kw)
def words_sprite(text, size, fg):  # transparent text only
    w = int(measure(text, size)) + 8; return Sticker(w, int(size * 1.2), None, [text], size, fg, ol=0, sh=0)

class El:
    def __init__(s, spr, cx, cy, t0, s0=2.0, rot0=10, idle=1.0, kind="slam", ph=0.0):
        s.spr, s.cx, s.cy, s.t0, s.s0, s.rot0, s.idle, s.kind, s.ph = spr, cx, cy, t0, s0, rot0, idle, kind, ph
def draw_el(img, e, t, events):
    if t < e.t0: return
    p = (t - e.t0) / 0.3
    if p >= 1: sc, ex, a = 1.0, 0.0, 1.0
    else:
        eb = ease_back(max(0, p)); sc = e.s0 + (1 - e.s0) * eb; ex = e.rot0 * (1 - min(1, p)) ** 2; a = min(1, p * 8)
    dy = e.idle * 3 * math.sin(t * 3.1 + e.ph) if e.idle else 0
    ex += (e.idle * 1.2 * math.sin(t * 2.3 + e.ph)) if (e.idle and p >= 1) else 0
    sp = e.spr.get(sc, ex if p < 1 else round(ex, 1))
    if a < 1: sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v: int(v * a)))
    img.paste(sp, (int(e.cx - sp.width / 2), int(e.cy + dy - sp.height / 2)), sp)

# ---------- beat layouts ----------
ELS = [[] for _ in range(6)]
def hook():
    E = ELS[0]; size = 124
    def row_w(items): return sum(measure(t, size) + 68 for t, *_ in items) + 22 * (len(items) - 1)
    rows = [[("아니,", OFF, 0.0 - 0.14, -3.5), ("세계", OFF, ws(1), 3)],
            [("기후회의가", OFF, ws(2), -2)],
            [("합의", VERM, ws(3), 3.5), ("없이", VERM, ws(4), -3)],
            [("끝났다고요", OFF, ws(5), 2)]]
    while max(row_w(r) for r in rows) > 768: size -= 4
    y = 425; xs0 = [66, 110, 70, 120]
    for ri, r in enumerate(rows):
        x = xs0[ri]
        for (txt, bg, t0, ang) in r:
            spr = block(txt, size, INK, bg, ang); wbox = measure(txt, size) + 68
            E.append(El(spr, x + wbox / 2, y, t0, 2.1, ang * 3, ph=ri + x)); x += wbox + 22
        y += int(size * 1.18) + 36 + 12
    q = Sticker(250, 250, YEL, ["?"], 230, INK, angle=9, ol=10, sh=14, circle=True)
    E.append(El(q, 230, y + 70, -0.12, 2.6, -25, idle=2.0))
def term():
    E = ELS[1]; t0 = BT[1]
    E.append(El(block("CNN 제목 속 표현", 56, INK, YEL, -3, padx=26, pady=12), 330, 365, t0, 1.8, -8))
    chunks = [("fail", ws(10), 190, OFF, INK, -3, 70), ("to agree", ws(11), 160, AZURE, INK, 2.5, 150), ("on", ws(13), 190, VERM, INK, -2, 90)]
    y = 450; GH = []
    for txt, t, size, bg, fg, ang, xo in chunks:
        while measure(txt, size) + 80 > 770 - xo - 14: size -= 4
        spr = block(txt, size, fg, bg, ang, padx=40, pady=26, ol=10, sh=16); w = measure(txt, size) + 80
        h = size * 1.18 + 52; cx = 62 + 14 + xo + w / 2
        cy = y + h / 2; GH.append((cx, cy, w, h)); E.append(El(spr, cx, cy, t, 2.2, ang * -4, ph=y)); y += int(h) + 34
    ELS[1] = E; ELS_GHOST[1] = GH
def meaning():
    E = ELS[2]; t0 = BT[2]
    E.append(El(block("뜻", 60, OFF, INK, -4, padx=34, pady=12), 140, 365, t0, 1.8, -10))
    E.append(El(block("fail to agree on", 50, OFF, INK, 2, padx=26, pady=10), 470, 365, t0 + 0.05, 1.6, 6))
    E.append(El(block("~에", 104, INK, OFF, -3), 170, 570, t0 + 0.08, 2.0, -10))
    s = 150
    E.append(El(block("합의하지", s, INK, OFF, -2, padx=40, pady=22, ol=10, sh=16), 62 + 20 + (measure("합의하지", s) + 80) / 2, 810, ws(14), 2.2, 12))
    E.append(El(block("못하다", s, INK, VERM, 2.5, padx=40, pady=22, ol=10, sh=16), 62 + 90 + (measure("못하다", s) + 80) / 2, 1050, ws(15), 2.2, -12))
def panel_text(E, panel_col, lines, hl_rows, size, x0, y0, wi, pad_t, word_idx0, lh, hl_pad=16):
    """lines: list of list of tokens; hl_rows: set of row idx forming ONE vermilion box (consecutive). Words pop at own start."""
    i = word_idx0; y = y0
    # highlight box geometry
    hl = sorted(hl_rows); sp_w = measure(" ", size)
    def rw(r): return sum(measure(t, size) for t in r) + sp_w * (len(r) - 1)
    if hl:
        bw = max(rw(lines[r]) for r in hl) + 2 * hl_pad + 8
        by0 = y0 + sum(lh for _ in range(hl[0])) + (0)
    rows_y = [y0 + lh * (r + .5) for r in range(len(lines))]
    # gaps: highlight box gets extra vertical padding -> shift rows after
    out_y = []; shift = 0
    for r in range(len(lines)):
        if hl and r == hl[0]: shift += hl_pad
        out_y.append(rows_y[r] + shift)
        if hl and r == hl[-1]: shift += hl_pad
    first_hl_word = None
    toks_idx = []; k = i
    for r, ln in enumerate(lines):
        row = []
        for t in ln: row.append(k); k += 1
        toks_idx.append(row)
    if hl:
        top = out_y[hl[0]] - lh / 2 - hl_pad * .6; bot = out_y[hl[-1]] + lh / 2 + hl_pad * .6
        spr = Sticker(int(bw), int(bot - top), VERM, ol=8, sh=10)
        E.append(El(spr, x0 + 8 + bw / 2, (top + bot) / 2, ws(toks_idx[hl[0]][0]) - .05, 1.5, 4, idle=0))
    for r, ln in enumerate(lines):
        x = x0 + (hl_pad + 4 if r in hl else 0)
        for tk, idx in zip(ln, toks_idx[r]):
            w = measure(tk, size); spr = words_sprite(tk, size, INK)
            E.append(El(spr, x + w / 2, out_y[r], ws(idx), 1.7, 8, idle=0)); x += w + sp_w
    return (out_y[-1] + lh / 2)
def example_en():
    E = ELS[3]; t0 = BT[3]; lines = [["Countries"], ["failed", "to"], ["agree", "on"], ["moving", "away"], ["from", "fossil"], ["fuels."]]
    size = 92
    while max(sum(measure(t, size) for t in l) + measure(" ", size) * (len(l) - 1) for l in lines) > 690: size -= 4
    lh = int(size * 1.2); pw = 788; px, py = 62, 400
    ph = lh * 6 + 32 + 100
    E.append(El(Sticker(pw, ph, OFF, ol=9, sh=14), px + pw / 2, py + ph / 2, t0, 1.35, 3, idle=0))
    E.append(El(block("예문", 58, OFF, INK, -4, padx=30, pady=10), 175, py - 12, t0 + .04, 1.8, -10))
    panel_text(E, OFF, lines, [1, 2], size, px + 40, py + 70, pw, 0, 16, lh)
def example_ko():
    E = ELS[4]; t0 = BT[4]; lines = [["각국은"], ["화석연료에서"], ["벗어나는", "데"], ["합의하지"], ["못했어요."]]
    size = 92
    while max(sum(measure(t, size) for t in l) + measure(" ", size) * (len(l) - 1) for l in lines) > 690: size -= 4
    lh = int(size * 1.22); pw = 788; px, py = 62, 400; ph = lh * 5 + 32 + 100
    E.append(El(Sticker(pw, ph, AZURE, ol=9, sh=14), px + pw / 2, py + ph / 2, t0, 1.35, -3, idle=0))
    E.append(El(block("해석", 58, YEL, INK, 4, padx=30, pady=10), 170, py - 12, t0 + .04, 1.8, 10))
    panel_text(E, AZURE, lines, [3, 4], size, px + 40, py + 70, pw, 0, 26, lh)
def payoff():
    E = ELS[5]; t0 = BT[5]
    E.append(El(block("저장해", 160, INK, YEL, -3, padx=44, pady=24, ol=10, sh=16), 62 + 40 + (measure("저장해", 160) + 88) / 2, 520, ws(32), 2.2, 12))
    E.append(El(block("두기", 160, INK, VERM, 2.5, padx=44, pady=24, ol=10, sh=16), 62 + 120 + (measure("두기", 160) + 88) / 2, 780, ws(33), 2.2, -12))
    E.append(El(block("fail to agree on", 54, OFF, INK, -2, padx=28, pady=12), 400, 1000, t0 + .25, 1.6, 6))
ELS_GHOST = {}
hook(); term(); meaning(); example_en(); example_ko(); payoff()
# bookmark icon + bouncing arrow (payoff) drawn procedurally
def bookmark_sticker():
    w, h, k, ol, sh = 190, 250, 2, 9, 14; pad = ol + sh + 4
    im = Image.new("RGBA", ((w + 2 * pad) * k, (h + 2 * pad) * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def poly(o, col):
        pts = [(pad - o, pad - o), (pad + w + o, pad - o), (pad + w + o, pad + h + o), (pad + w / 2, pad + h - 70 + o * 1.4), (pad - o, pad + h + o)]
        return [(x * k, y * k) for x, y in pts]
    sh_pts = [(x + sh * k, y + sh * k) for x, y in poly(ol, 0)]
    d.polygon(sh_pts, fill=BLK); d.polygon(poly(ol, 0), fill=BLK); d.polygon(poly(0, 0), fill=OFF)
    s = Sticker(1, 1, None); s.src = im; s.angle = 5; s.w, s.h, s.pad = w, h, pad; s._c = {}
    return s
BOOK = bookmark_sticker()
def arrow_sticker():
    w, h, k, ol, sh = 170, 210, 2, 8, 12; pad = ol + sh + 4
    im = Image.new("RGBA", ((w + 2 * pad) * k, (h + 2 * pad) * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def poly(o):
        pts = [(w * .3, 0), (w * .7, 0), (w * .7, h * .5), (w, h * .5), (w / 2, h), (0, h * .5), (w * .3, h * .5)]
        cx, cy = w / 2, h / 2
        return [((pad + cx + (x - cx) + (o if x > cx else -o if x < cx else 0)) * k, (pad + y + (o if y >= h * .99 else -o if y <= 0 else 0)) * k) for x, y in pts]
    d.polygon([(x + sh * k, y + sh * k) for x, y in poly(ol)], fill=BLK); d.polygon(poly(ol), fill=BLK); d.polygon(poly(0), fill=VERM)
    s = Sticker(1, 1, None); s.src = im; s.angle = 0; s._c = {}
    return s
ARROW = arrow_sticker()

# ---------- background ----------
P = 120
yy, xx = np.mgrid[0:H + P, 0:W]; STRIPE = (((xx + yy) % P) < 34)
LUT = np.array([INK, BG1], np.uint8)
def bg_frame(t):
    k = int(t * 90) % P
    return Image.fromarray(LUT[STRIPE[k:k + H].astype(np.uint8)], "RGB")
rng = np.random.default_rng(7)
CONF = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(-40, 40), rng.uniform(25, 80), rng.uniform(0, 6.28),
         rng.integers(0, 3), rng.uniform(20, 46), rng.uniform(-90, 90)) for _ in range(16)]
def confetti(img, t):
    d = ImageDraw.Draw(img)
    for (x, y, vx, vy, a0, kind, sz, om) in CONF:
        cx, cy = (x + vx * t) % (W + 100) - 50, (y + vy * t) % (H + 100) - 50; a = math.radians(a0 * 57 + om * t)
        col = (AZURE, VERM, YEL)[int(kind)]
        if kind == 2:  # plus
            for dx, dy in ((1, 0), (0, 1)):
                c, s = math.cos(a), math.sin(a)
                ex, ey = (c * dx - s * dy) * sz, (s * dx + c * dy) * sz
                d.line((cx - ex, cy - ey, cx + ex, cy + ey), fill=BLK, width=18);
            for dx, dy in ((1, 0), (0, 1)):
                c, s = math.cos(a), math.sin(a)
                ex, ey = (c * dx - s * dy) * sz, (s * dx + c * dy) * sz
                d.line((cx - ex, cy - ey, cx + ex, cy + ey), fill=col, width=9)
        else:
            n = 4 if kind == 0 else 3
            pts = [(cx + sz * math.cos(a + i * 2 * math.pi / n + (math.pi / 4 if n == 4 else 0)), cy + sz * math.sin(a + i * 2 * math.pi / n + (math.pi / 4 if n == 4 else 0))) for i in range(n)]
            d.polygon([(x + 8, y + 8) for x, y in pts], fill=BLK); d.polygon(pts, fill=col, outline=BLK, width=5)

TH = np.linspace(0, 2 * np.pi, 220, endpoint=False)
def r_circle(th): return np.ones_like(th)
def r_square(th): return (np.abs(np.cos(th)) ** 5 + np.abs(np.sin(th)) ** 5) ** (-0.2) / 1.2
def r_star(th):
    f = (th * 10 / (2 * np.pi)) % 1; return 0.56 + 0.44 * (np.abs(f - 0.5) * 2)
KEYS = [r_circle, r_square, r_star]
def morph_r(u):
    k = int(u) % 3; f = u % 1; f = f * f * (3 - 2 * f)
    return (1 - f) * KEYS[k](TH) + f * KEYS[(k + 1) % 3](TH)
RS = 440; LS = int(2 * RS * 1.2) + 60
EVENTS = [0.0 - 0.1, ws(1), ws(2), ws(3), ws(4), ws(5), ws(10), ws(11), ws(13)] + BT
def beat_idx(t):
    return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
def pulse(t):
    return sum(0.07 * math.exp(-(t - e) / 0.11) for e in EVENTS if 0 <= t - e < 0.6)
def shape_layer(t, col):
    u = 0.42 * t + 0.0; r = morph_r(u) * (1 + 0.025 * math.sin(t * 5.0)); rot = math.radians(t * 14)
    S = LS * 2; c = S / 2; sc = (1 + pulse(t)) * RS * 2
    th = TH + rot
    ro = r * sc + 20
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = lambda rr, o=0: [(c + o + rr[i] * math.cos(th[i]), c + o + rr[i] * math.sin(th[i])) for i in range(len(th))]
    d.polygon(pts(ro, 44), fill=BLK); d.polygon(pts(ro), fill=BLK); d.polygon(pts(r * sc), fill=col)
    return im.resize((LS, LS), Image.BOX)
SHAPE_CX, SHAPE_CY = 520, 760

# ---------- bird ----------
ENV = BIRD.envelope(MP3, FPS, int(TOTAL * FPS) + 3)
_bc = {}
def bird_img(a):
    q = round(a * 16) / 16
    if q in _bc: return _bc[q]
    sp = BIRD.sprite(q); al = sp.getchannel("A")
    ol = al.filter(ImageFilter.MaxFilter(9)); pad = 20
    im = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
    blk = Image.new("RGBA", ol.size, (0, 0, 0, 255)); blk.putalpha(ol)
    im.alpha_composite(blk, (pad + 10, pad + 10)); im.alpha_composite(blk, (pad, pad)); im.alpha_composite(sp, (pad, pad))
    _bc[q] = im; return im
PLATS = {}
def plat(i):
    if i not in PLATS: PLATS[i] = Sticker(330, 72, PLAT_COL[i], ol=8, sh=12)
    return PLATS[i]
BCX, PLAT_TOP = 690, 1425
def draw_bird(img, t, fi):
    bi = beat_idx(t); dt = t - BT[bi]
    hop = 28 * math.sin(math.pi * dt / 0.36) if dt < 0.36 else 0
    sq = 1 - 0.0
    ps = plat(bi).get(); img.paste(ps, (int(BCX - ps.width / 2), PLAT_TOP - 8 - 20 + 8), ps)
    b = bird_img(float(ENV[fi]))
    img.paste(b, (int(BCX - b.width / 2), int(PLAT_TOP - b.height + 34 - hop)), b)

# ---------- chrome ----------
PILL = block("NEWS ENGLISH · CNN", 38, INK, AZURE, -2, padx=24, pady=8, ol=6, sh=8)
HANDLE_F = font(40, BOLD_F)
def draw_chrome(img):
    img.paste(PILL.get(), (62 - 6, 222), PILL.get())
    d = ImageDraw.Draw(img); txt = "지나쌤영어  @jina.ssam_english"
    d.text((W // 2 + 2, 1590 + 2), txt, font=HANDLE_F, fill=BLK, anchor="mm")
    d.text((W // 2, 1588), txt, font=HANDLE_F, fill=OFF, anchor="mm")

def draw_ghosts(img, t):
    if 1 in ELS_GHOST and beat_idx(t) == 1:
        d = ImageDraw.Draw(img)
        for (cx, cy, w, h), e in zip(ELS_GHOST[1], ELS[1][1:]):
            if t < e.t0:
                x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
                for xa in range(int(x0), int(x1), 40): d.line((xa, y0, min(xa + 22, x1), y0), fill=OFF, width=6); d.line((xa, y1, min(xa + 22, x1), y1), fill=OFF, width=6)
                for ya in range(int(y0), int(y1), 40): d.line((x0, ya, x0, min(ya + 22, y1)), fill=OFF, width=6); d.line((x1, ya, x1, min(ya + 22, y1)), fill=OFF, width=6)

def wipe(img, t):
    for i, b in enumerate(BT[1:], 1):
        dt = t - b
        if 0 <= dt < 0.26:
            p = dt / 0.26; x = -300 + (W + 600) * p
            d = ImageDraw.Draw(img)
            d.polygon([(x - 40, 0), (x + 220, 0), (x + 120, H), (x - 140, H)], fill=BLK)
            d.polygon([(x, 0), (x + 180, 0), (x + 80, H), (x - 100, H)], fill=YEL)

def frame(t, fi):
    bi = beat_idx(t); img = bg_frame(t); confetti(img, t)
    sl = shape_layer(t, SHAPE_COL[bi]); img.paste(sl, (SHAPE_CX - LS // 2, SHAPE_CY - LS // 2), sl)
    wipe(img, t); draw_ghosts(img, t)
    for e in ELS[bi]: draw_el(img, e, t, EVENTS)
    if bi == 5:
        t0 = BT[5]
        if t >= ws(33):
            b = BOOK.get(min(1, 1), 0); img.paste(b, (730 - b.width // 2, 850 - b.height // 2 + int(2 * math.sin(t * 4))), b)
            bounce = abs(math.sin((t - ws(33)) * 7.5)) * 34
            a = ARROW.get(); img.paste(a, (730 - a.width // 2, int(610 - bounce) - a.height // 2), a)
    draw_bird(img, t, fi); draw_chrome(img)
    return img

MARKS = {"hook_0.0": 0.0, "hook_0.3": 0.3, "hook_1.0": 1.0, "hook_end": 3.5, "term": 7.6, "meaning": 9.2, "example_en": 13.5,
         "example_ko": 17.4, "payoff": 18.9}
def render():
    os.makedirs(FR, exist_ok=True); nfr = int(round(TOTAL * FPS)); out = f"{OUT}/kw3_{RID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", MP3, "-filter_complex", "[1:a]apad,aformat=channel_layouts=stereo[a]", "-map", "0:v", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "1", "-c:a", "aac", "-b:a", "192k",
           "-ar", "44100", "-t", f"{TOTAL:.3f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE); mk = {round(v * FPS): k for k, v in MARKS.items()}
    for i in range(nfr):
        im = frame(i / FPS, i); p.stdin.write(im.tobytes())
        if i in mk: im.save(f"{FR}/kw3_{RID}_{mk[i]}.png")
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg")
    print("done", out, TOTAL)

def report_contrast():
    pairs = {"ink/off-white (hook words, panel)": (INK, OFF), "ink/vermilion (합의 없이, highlight)": (INK, VERM), "ink/azure (panel ko, term)": (INK, AZURE),
             "ink/yellow (?, 저장해, pill)": (INK, YEL), "off-white/ink (labels)": (OFF, INK), "yellow/ink (해석 label)": (YEL, INK), "handle off-white/midnight": (OFF, INK)}
    for k, (a, b) in pairs.items(): print(f"{contrast(a, b):5.2f}  {k}")

if __name__ == "__main__":
    report_contrast()
    if "--frames" in sys.argv:
        os.makedirs(FR, exist_ok=True)
        for k, v in MARKS.items(): frame(v, int(v * FPS)).save(f"{FR}/kw3_{RID}_{k}.png")
    else: render()
