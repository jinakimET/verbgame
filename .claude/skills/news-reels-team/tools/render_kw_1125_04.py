#!/usr/bin/env python3
"""kw 1125 / 04 'as of' : INFINITE ZOOM tunnel (log-space nested window frames) + TEXT SCRAMBLE + PARTICLES.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw_1125_04.py [--frames t1,t2,...]   (frames only, no video)
Output: 06_keyword_reels/kw_04.mp4, frames in 06_keyword_reels/frames/"""
import os, sys, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
RID = "04"; W, H = 1080, 1920; FPS = 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
MP3 = f"{ROOT}/audio/kw_{RID}.mp3"
FD = "/usr/share/fonts/opentype/noto/NotoSansCJK-"
_fc = {}
def font(sz, w="Black"):
    k = (sz, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}{w}.ttc", sz, index=1)
    return _fc[k]
NAVY = (0, 41, 65); BLUE = (182, 223, 237); CORAL = (253, 110, 110); WHITE = (255, 255, 255)
CX = 456  # centre of the safe area (x 62..850)

def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

_s = json.load(open(f"{ROOT}/03_script/keyword_scripts.json"))["reels"]
spec = _s[RID] if isinstance(_s, dict) else [x for x in _s if str(x["id"]) == RID][0]
WK = json.load(open(f"{ROOT}/audio/words_kw.json"))[RID]
words = WK["words"]; BT = [b["start"] for b in WK["beats"]]
ROLES = [b["role"] for b in WK["beats"]]
assert ROLES == [b["role"] for b in spec["beats"]]
AUDIO_DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
TOTAL = AUDIO_DUR + TAIL; NF = int(round(TOTAL * FPS))
def ws(i): return words[i]["s"]
def beat_idx(t):
    b = 0
    for k, s in enumerate(BT):
        if t >= s - 1e-6: b = k
    return b

# ------------------------------------------------------------------ infinite-zoom tunnel
HW, HH = 540, 960
TCX, TCY = 456, 700            # vanishing point (full-res px)
XX = ((np.arange(HW, dtype=np.float32) + .5) * 2 - TCX)[None, :] * np.ones((HH, 1), np.float32)
YY = ((np.arange(HH, dtype=np.float32) + .5) * 2 - TCY)[:, None] * np.ones((1, HW), np.float32)
STEP = 0.34  # ln ratio between nested frames (never loops: log space)
C = lambda *a: np.array(a, np.float32)
SCHEMES = {
    "hook":       dict(fills=[C(0, 41, 65), C(0, 56, 88), C(0, 41, 65), C(98, 48, 66)], rim=C(182, 223, 237), rate=.00, a0=0.0, dark=.80),
    "term":       dict(fills=[C(0, 41, 65), C(10, 74, 110), C(0, 41, 65), C(0, 60, 95)], rim=C(253, 110, 110), rate=.10, a0=.45, dark=.85),
    "meaning":    dict(fills=[C(18, 88, 128), C(0, 41, 65), C(28, 108, 148), C(0, 41, 65)], rim=C(182, 223, 237), rate=-.12, a0=-.4, dark=.80),
    "example_en": dict(fills=[C(0, 41, 65), C(0, 50, 80), C(110, 45, 62), C(0, 50, 80)], rim=C(182, 223, 237), rate=.06, a0=.2, dark=.80),
    "example_ko": dict(fills=[C(0, 35, 56), C(12, 70, 104), C(0, 35, 56), C(4, 58, 92)], rim=C(255, 170, 170), rate=-.09, a0=-.7, dark=.80),
    "payoff":     dict(fills=[C(120, 40, 60), C(0, 41, 65), C(160, 60, 75), C(0, 41, 65)], rim=C(255, 233, 233), rate=.20, a0=.9, dark=.82),
}
def lurch(t):
    return sum(0.9 * (1 - math.exp(-(t - b) / 0.18)) for b in BT if t > b)
def zoomphase(t): return 0.9 * t + lurch(t)
def tunnel(t, bi):
    sc = SCHEMES[ROLES[bi]]; th = sc["a0"] + sc["rate"] * (t - BT[bi]) + (0.05 * math.sin(t * 1.3) if ROLES[bi] == "hook" else 0)
    c, s = math.cos(th), math.sin(th)
    xr = c * XX + s * YY; yr = -s * XX + c * YY
    a = (xr / 0.78) ** 2; a *= a; b = yr ** 2; b *= b
    d = np.sqrt(np.sqrt(a + b)) + 1e-3
    p = np.log(d) / STEP - zoomphase(t)
    n = np.floor(p); f = (p - n).astype(np.float32); ni = n.astype(np.int32)
    idx = (ni * 3 + ni // 4) % 4
    fills = np.stack(sc["fills"])
    col = fills[idx] * (0.62 + 0.55 * f)[..., None]
    r = np.exp(-(f / 0.055) ** 2) * np.clip(d / 28, 0, 1)
    col = col * (1 - r[..., None] * .8) + sc["rim"][None, None, :] * (r[..., None] * .8)
    col *= (0.40 + 0.60 * np.clip(d / 520, 0, 1) ** .5)[..., None]
    glow = np.exp(-(d / 60) ** 2)[..., None] * (sc["rim"] * .35)
    col = (col + glow) * sc["dark"]
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGB").resize((W, H), Image.BILINEAR)
    return im.convert("RGBA")

# ------------------------------------------------------------------ particles (dust / stars drifting to camera)
rng = np.random.default_rng(7); NP = 150
P_ANG = rng.uniform(0, 2 * np.pi, NP); P_Z0 = rng.uniform(0, 1, NP); P_SZ = rng.uniform(.6, 1.6, NP)
P_COL = [BLUE, CORAL, WHITE, BLUE][0:1] * 0 + [([BLUE, CORAL, WHITE, BLUE][i % 4]) for i in range(NP)]
P_STAR = rng.uniform(0, 1, NP) < .3
def particles(img, t, th):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    z = (P_Z0 - 0.07 * zoomphase(t)) % 1.0
    z = np.maximum(z, 0.02); rr = 36 / z
    ang = P_ANG + th
    x = TCX + rr * np.cos(ang) * .78; y = TCY + rr * np.sin(ang)
    sz = (1.2 + 7 * (1 - z)) * P_SZ; al = np.clip((1 - z) * 3, 0, 1) * np.clip(z * 6, 0, 1) * .9
    for i in range(NP):
        if not (-30 < x[i] < W + 30 and -30 < y[i] < H + 30) or al[i] < .05: continue
        col = P_COL[i] + (int(255 * al[i]),)
        s = sz[i]
        if P_STAR[i]:
            d.polygon([(x[i], y[i] - 2 * s), (x[i] + .45 * s, y[i] - .45 * s), (x[i] + 2 * s, y[i]), (x[i] + .45 * s, y[i] + .45 * s),
                       (x[i], y[i] + 2 * s), (x[i] - .45 * s, y[i] + .45 * s), (x[i] - 2 * s, y[i]), (x[i] - .45 * s, y[i] - .45 * s)], fill=col)
        else:
            d.ellipse((x[i] - s, y[i] - s, x[i] + s, y[i] + s), fill=col)
    img.alpha_composite(ov)

# ------------------------------------------------------------------ sprites / text
def put(img, spr, x, y):
    x, y = int(round(x)), int(round(y)); sw, sh = spr.size
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(img.width, x + sw), min(img.height, y + sh)
    if x1 <= x0 or y1 <= y0: return
    img.alpha_composite(spr.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))
def fade(spr, a):
    if a >= .999: return spr
    s = spr.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * max(0, a)))); return s
def back(p):
    p = min(1, max(0, p)); c = 1.70158; q = p - 1; return 1 + (c + 1) * q ** 3 + c * q ** 2
def scaled(spr, s):
    return spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.BILINEAR)
def put_c(img, spr, cx, cy, s=1.0, a=1.0, rot=0):
    if s != 1.0: spr = scaled(spr, s)
    if rot: spr = spr.rotate(rot, Image.BICUBIC, expand=True)
    if a < .999: spr = fade(spr, a)
    put(img, spr, cx - spr.width / 2, cy - spr.height / 2)
_tc = {}
PAD = 14
def tspr(text, sz, fill=WHITE, stroke=None, alpha=1.0):
    k = (text, sz, fill, stroke, round(alpha, 2))
    if k in _tc: return _tc[k]
    f = font(sz); wd = int(math.ceil(f.getlength(text))) + 2 * PAD; ht = int(sz * 1.45) + 2 * PAD
    im = Image.new("RGBA", (wd, ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sw = max(0, int(sz / 16)) if stroke else 0
    d.text((PAD, PAD + int(sz * .06)), text, font=f, fill=fill + (255,), stroke_width=sw, stroke_fill=(stroke or NAVY) + (255,))
    if alpha < 1: im = fade(im, alpha)
    _tc[k] = im; return im
def rr_sprite(w, h, fill, outline=None, ow=6, r=None, alpha=255, top_arch=False):
    pad = 24; s = 2
    im = Image.new("RGBA", ((w + 2 * pad) * s, (h + 2 * pad) * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rad = (r if r is not None else h // 2) * s
    box = (pad * s, pad * s, (pad + w) * s, (pad + h) * s)
    kw = dict(corners=(True, True, False, False)) if top_arch else {}
    d.rounded_rectangle(box, radius=rad, fill=fill + (alpha,), outline=(outline + (255,)) if outline else None, width=ow * s, **kw)
    return im.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
def fit(text, sz, maxw):
    while font(sz).getlength(text) > maxw and sz > 30: sz -= 2
    return sz

# --- layout: a line of words, each (idx_in_words, text); returns placements
class Line:
    def __init__(self, items, size, cy, maxw=788, cx=CX, gap=.26, fill=WHITE, ghost_fill=None, stroke=NAVY):
        txt = " ".join(t for _, t in items); self.size = fit(txt, size, maxw)
        f = font(self.size); sp = f.getlength(" ") * (gap / .26) if False else self.size * gap
        ws_ = [f.getlength(t) for _, t in items]; tot = sum(ws_) + sp * (len(items) - 1)
        x = cx - tot / 2; self.items = []
        for (i, t), w in zip(items, ws_):
            self.items.append(dict(i=i, text=t, x=x + w / 2, w=w)); x += w + sp
        self.cy = cy; self.fill = fill; self.stroke = stroke; self.gfill = ghost_fill or fill
        self.tot = tot
    def draw(self, img, t, t0, dy=0, ghost_a=.26, pop_t=.22, fill=None, stroke=None, special=None, slide=0):
        for it in self.items:
            s = ws(it["i"]); fl = fill or self.fill; sk = stroke or self.stroke
            if t < s:
                spr = tspr(it["text"], self.size, fl, sk, ghost_a)
                put_c(img, spr, it["x"], self.cy + dy)
            else:
                q = (t - s) / pop_t
                sc = .82 + .18 * back(q) if q < 1 else 1.0
                spr = special(it, t) if special else None
                if spr is None: spr = tspr(it["text"], self.size, fl, sk)
                put_c(img, spr, it["x"] + slide * (1 - min(1, q)), self.cy + dy - 14 * (1 - min(1, q)), sc, min(1, .35 + q))

# --- scramble
POOL_D = "0123456789"; POOL_L = "abcdefghijklmnopqrstuvwxyz"; POOL_H = "#%&*+?"
def rnd_char(t, k, target):
    r = np.random.default_rng(int(t * 15) * 131 + k * 7 + 3)
    if target.isdigit(): return POOL_D[r.integers(10)]
    if target.isalpha(): return POOL_L[r.integers(26)]
    return POOL_H[r.integers(len(POOL_H))]
def scramble_sprite(target, size, res_times, t, fill_done, fill_scr, stroke=NAVY, fixed=None, keep=" ,.+"):
    """target string; each char resolves at res_times[k]. returns RGBA sprite (glyphs centred in target-width slots)."""
    f = font(size); sw = max(1, size // 16) if stroke else 0
    slots = []; x = 0
    for ch in target:
        w = f.getlength(ch); slots.append((x, w)); x += w
    wd = int(x) + 2 * PAD; ht = int(size * 1.45) + 2 * PAD
    im = Image.new("RGBA", (wd, ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k, ch in enumerate(target):
        if ch in keep and ch != "+" or ch == " ": show = ch; done = True
        else:
            done = t >= res_times[k]; show = ch if done else rnd_char(t, k, ch)
        w = slots[k][1]; gw = f.getlength(show)
        d.text((PAD + slots[k][0] + (w - gw) / 2, PAD + int(size * .06)), show, font=f, fill=(fill_done if done else fill_scr) + (255,),
               stroke_width=sw, stroke_fill=stroke + (255,) if stroke else None)
    return im

# ------------------------------------------------------------------ bird in a window
WIN_W, WIN_H, WIN_Y = 330, 280, 1235
WIN_BACK = rr_sprite(WIN_W, WIN_H, (0, 26, 42), outline=BLUE, ow=7, r=WIN_W // 2, top_arch=True)
SILL = rr_sprite(WIN_W + 70, 34, CORAL, r=12)
FRONT = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ENV = bird.envelope(MP3, FPS, NF)
HANDLE = tspr("지나쌤영어  @jina.ssam_english", 40, BLUE, None)
def draw_bird(img, i, t):
    cx = CX; wx = cx - WIN_BACK.width / 2
    put(img, WIN_BACK, wx, WIN_Y - 24)
    bob = 5 * math.sin(t * 3.0)
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bird.place(tmp, float(ENV[min(i, len(ENV) - 1)]), cx, WIN_Y + WIN_H - 20 + int(bob) + 0)
    # clip to window interior (above the sill line): keep everything above sill, windows' sides naturally wide enough
    img.alpha_composite(tmp)
    put(img, SILL, cx - SILL.width / 2, WIN_Y + WIN_H - 24 - 8)
    # window outline front (sides) for depth
    put(img, tspr("", 10), 0, 0)

# ------------------------------------------------------------------ beat content
def panel(w, h, cy, cx=CX, outline=BLUE, alpha=170):
    return rr_sprite(w, h, NAVY, outline=outline, ow=5, r=46, alpha=alpha)
HOOK = [Line([(0, "아니,")], 150, 350, fill=CORAL),
        Line([(1, "파리에"), (2, "이런")], 104, 520),
        Line([(3, "하녀방이")], 104, 640)]
HOOK_TAIL = Line([(5, "개가"), (6, "넘는다고요?")], 96, 1135)
NUM_T = "90,000+"; NUM_SZ = fit(NUM_T, 210, 700)
PANEL_NUM = rr_sprite(770, 250, NAVY, outline=BLUE, ow=6, r=56, alpha=215)
PANEL_NUM_ON = rr_sprite(770, 250, CORAL, r=56)
SUB_9 = tspr("= 9만", 76, BLUE)
TERM_STK_T = "2022년 기준"; STK_SZ = 96
STK_BOX = rr_sprite(int(font(STK_SZ).getlength(TERM_STK_T)) + 90, 150, CORAL, r=30)
STK_BOX_G = fade(STK_BOX, .3)
EN_TERM = "as of"; EN_SZ = fit(EN_TERM, 320, 770)
MEAN_P1 = rr_sprite(788, 210, NAVY, outline=BLUE, ow=6, r=56, alpha=225)
MEAN_P2 = rr_sprite(788, 210, CORAL, r=56)
CHIP = rr_sprite(330, 130, CORAL, r=34)
EXL_A = Line([(15, "As"), (16, "of"), (17, "2025,")], 120, 500, maxw=720, fill=NAVY, stroke=None)
EXL_A.stroke = None
EXL_B = Line([(18, "the"), (19, "shop"), (20, "has")], 92, 735)
EXL_C = Line([(21, "40"), (22, "branches.")], 92, 880)
BOX_EN = rr_sprite(int(EXL_A.tot) + 80, 176, CORAL, r=40)
PAN_EN = rr_sprite(788, 330, NAVY, outline=BLUE, ow=5, r=56, alpha=205)
KO1 = Line([(23, "2025년"), (24, "기준으로")], 92, 480, maxw=700, fill=NAVY, stroke=None)
KO2 = Line([(25, "그"), (26, "가게는")], 112, 700)
KO3 = Line([(27, "지점이"), (28, "40개다.")], 112, 860)
BOX_KO = rr_sprite(int(KO1.tot) + 80, 160, CORAL, r=38)
PAN_KO = rr_sprite(788, 400, NAVY, outline=CORAL, ow=5, r=56, alpha=205)
PAY_BOX = rr_sprite(790, 330, CORAL, r=70)
PAY_SZ = fit(EN_TERM, 300, 700)
PILL_W, PILL_H = 600, 150
PILL = rr_sprite(PILL_W, PILL_H, BLUE, r=75)
def pill_content(a=1.0):
    im = Image.new("RGBA", PILL.size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ox, oy = 24 + 56, 24 + 36
    d.polygon([(ox, oy), (ox + 54, oy), (ox + 54, oy + 80), (ox + 27, oy + 58), (ox, oy + 80)], fill=CORAL + (255,))
    t = tspr("저장해 두기", 70, NAVY, None)
    im.alpha_composite(t, (24 + 150, 24 + int((PILL_H - t.height) / 2) + 6))
    return im
PILL_C = pill_content()
PILL_FULL = PILL.copy(); PILL_FULL.alpha_composite(PILL_C)

def scr_term_en(t, size, t_as, t_of, done, scr):
    # 'as of' : letters a,s resolve staggered from word 'as' start, o,f from 'of.' start
    rt = [t_as, t_as + .08, 0, t_of, t_of + .08]
    return scramble_sprite(EN_TERM, size, rt, t, done, scr)

def render(i):
    t = i / FPS; bi = beat_idx(t); role = ROLES[bi]; t0 = BT[bi]; pp = t - t0
    sc = SCHEMES[role]; th = sc["a0"] + sc["rate"] * (t - t0)
    img = tunnel(t, bi)
    particles(img, t, th * .6)
    # beat-change flash
    if pp < .12 and t > .1:
        fl = Image.new("RGBA", (W, H), BLUE + (int(110 * (1 - pp / .12)),)); img.alpha_composite(fl)
    if role == "hook":
        for L in HOOK:
            if L.items[0]["i"] == 0:
                s0 = ws(0); q = t / .30
                scl = 1 + .45 * (1 - back(q)) if q < 1 else 1.0
                shake = 10 * math.sin(t * 90) * max(0, 1 - t / .35)
                spr = tspr("아니,", L.size, CORAL, NAVY); put_c(img, spr, L.items[0]["x"] + shake, L.cy, max(.9, scl))
            else:
                L.draw(img, t, 0)
        # number block : scramble until '9만' (2.24) then resolve letter by letter
        t9 = ws(4); res = [t9 + .07 * k for k in range(len(NUM_T))]
        done_all = t >= res[-1]; cy = 850
        q = (t - t9) / .3; bs = 1.0 + (.12 * (1 - back(q)) if 0 <= q < 1 else 0) + .012 * math.sin(t * 6)
        put_c(img, PANEL_NUM_ON if t >= t9 else PANEL_NUM, CX, cy, bs)
        spr = scramble_sprite(NUM_T, NUM_SZ, res, t, NAVY, BLUE, stroke=None if t >= t9 else NAVY)
        put_c(img, spr, CX, cy + 4, bs)
        if t >= t9: put_c(img, SUB_9, CX, 1030, .8 + .2 * back((t - t9) / .25), min(1, (t - t9) / .15))
        HOOK_TAIL.draw(img, t, 0, dy=0 if t >= t9 else 0)
    elif role == "term":
        # sticker "2022년 기준" : digits scramble 4.16 -> 4.9, '기준' pops with word 8
        s7, s8 = ws(7), ws(8)
        rt = [s7 + .12 * k for k in range(4)]
        q = pp / .3; sc_ = .7 + .3 * back(q)
        sy = 400 + 6 * math.sin(t * 2.2)
        put_c(img, STK_BOX, CX, sy, sc_ * (1 + .015 * math.sin(t * 5)), 1, rot=5)
        txt = "2022년 기준"
        f = font(STK_SZ); gh = Image.new("RGBA", (int(f.getlength(txt)) + 2 * PAD, int(STK_SZ * 1.45) + 2 * PAD), (0, 0, 0, 0))
        left = scramble_sprite("2022", STK_SZ, rt, t, NAVY, (120, 30, 40), stroke=None, keep="")
        gh.alpha_composite(left, (0, 0)); wl = f.getlength("2022")
        g2 = tspr("년", STK_SZ, NAVY, None); gh.alpha_composite(g2, (int(wl), 0))
        wr = f.getlength("2022년 ")
        g3 = tspr("기준", STK_SZ, NAVY, None, 1.0 if t >= s8 else .3); gh.alpha_composite(g3, (int(wr), 0))
        put_c(img, gh, CX, sy, sc_ * (1 + .015 * math.sin(t * 5)), 1, rot=5)
        # 영어로, label
        s9 = ws(9)
        put_c(img, tspr("영어로,", 70, BLUE if t >= s9 else BLUE, NAVY, 1.0 if t >= s9 else .3), CX, 650, .85 + .15 * back((t - s9) / .25) if t >= s9 else 1)
        # big scrambled 'as of'
        t_as, t_of = ws(10), ws(11)
        spr = scr_term_en(t, EN_SZ, t_as, t_of, WHITE, BLUE)
        st = 1.0 + (.1 * (1 - back((t - t_as) / .3)) if 0 <= t - t_as < .3 else 0) + (.08 * (1 - back((t - t_of) / .3)) if 0 <= t - t_of < .3 else 0)
        put_c(img, spr, CX, 930, st)
        if t >= t_of + .15:
            u = min(1, (t - t_of - .15) / .3); w = int(540 * u)
            if w > 4: ImageDraw.Draw(img).rounded_rectangle((CX - w / 2, 1100, CX + w / 2, 1114), radius=7, fill=CORAL + (255,))
    elif role == "meaning":
        # chip 'as of' top, two stacked panels, words appear at their start
        put_c(img, CHIP, CX, 380, .9)
        put_c(img, tspr("as of", 96, NAVY, None), CX, 384, .9)
        s12, s13 = ws(12), ws(13)
        for k, (pan, txt, s, fillc, cy) in enumerate(((MEAN_P1, "~ 기준으로", s12, WHITE, 620), (MEAN_P2, "~ 현재", s13, NAVY, 880))):
            on = t >= s; q = (t - s) / .3
            scl = (.82 + .18 * back(q)) if on and q < 1 else 1
            put_c(img, pan, CX, cy + 4 * math.sin(t * 2 + k), scl, 1 if on else .25)
            put_c(img, tspr(txt, 112, fillc, NAVY if fillc == WHITE else None, 1.0 if on else .3), CX + (30 * (1 - min(1, max(0, q))) if on else 0), cy + 4 * math.sin(t * 2 + k), scl)
        s14 = ws(14)
        if t >= s14:
            q = (t - s14) / .3
            put_c(img, tspr("라는 뜻", 64, BLUE, NAVY), CX, 1060, .85 + .15 * back(q), min(1, q * 2))
    elif role == "example_en":
        put_c(img, PAN_EN, CX, 810, 1, 1)
        s15 = ws(15); put_c(img, BOX_EN, CX, 500 + 4 * math.sin(t * 2), .85 + .15 * back((t - t0) / .3))
        def spec_2025(it, tt):
            if it["text"] != "2025,": return None
            return scramble_sprite("2025,", EXL_A.size, [ws(17) + .09 * k for k in range(5)], tt, NAVY, (120, 30, 40), stroke=None)
        EXL_A.draw(img, t, 0, dy=4 * math.sin(t * 2), fill=NAVY, ghost_a=.3, special=spec_2025)
        EXL_B.draw(img, t, 0); EXL_C.draw(img, t, 0)
    elif role == "example_ko":
        put_c(img, PAN_KO, CX, 780, 1, 1)
        put_c(img, BOX_KO, CX - 10, 480 + 4 * math.sin(t * 2), .85 + .15 * back(pp / .3))
        KO1.draw(img, t, 0, dy=4 * math.sin(t * 2), fill=NAVY, ghost_a=.3, slide=60)
        KO2.draw(img, t, 0, slide=-60); KO3.draw(img, t, 0, slide=60)
    else:  # payoff
        t_as, t_of = ws(29), ws(30)
        pb = .85 + .15 * back(pp / .3)
        put_c(img, PAY_BOX, CX, 640, pb * (1 + .012 * math.sin(t * 6)))
        rt = [t_as, t_as + .08, 0, t_of, t_of + .08]
        spr = scramble_sprite(EN_TERM, PAY_SZ, rt, t, NAVY, (120, 30, 40), stroke=None)
        put_c(img, spr, CX, 650, pb)
        s31 = ws(31); on = t >= s31
        if on:
            q = (t - s31) / .3; bs = (.8 + .2 * back(q)) * (1 + .03 * math.sin((t - s31) * 9))
            put_c(img, PILL_FULL, CX, 1010, bs)
            for k in range(8):   # little star burst
                ang = k * math.pi / 4 + .3; r = 100 + 330 * min(1, (t - s31) / .5) ** .6
                al = max(0, 1 - (t - s31) / .8)
                if al > 0:
                    x = CX + math.cos(ang) * r * 1.0; y = 1010 + math.sin(ang) * r * .45
                    ImageDraw.Draw(img).polygon([(x, y - 14), (x + 4, y - 4), (x + 14, y), (x + 4, y + 4), (x, y + 14), (x - 4, y + 4), (x - 14, y), (x - 4, y - 4)], fill=CORAL + (int(255 * al),))
        else:
            put_c(img, PILL_FULL, CX, 1010, .9, .25)
    draw_bird(img, i, t)
    put(img, HANDLE, (W - HANDLE.width) / 2, 1588 - 14)
    return img.convert("RGB")

def checks():
    pairs = [("hook word BLUE/NAVY", BLUE, NAVY), ("hook white/NAVY", WHITE, NAVY), ("아니, CORAL/NAVY", CORAL, NAVY),
             ("number NAVY/CORAL box", NAVY, CORAL), ("sticker NAVY/CORAL", NAVY, CORAL), ("as of WHITE/NAVY stroke", WHITE, NAVY),
             ("meaning WHITE/NAVY panel", WHITE, NAVY), ("meaning NAVY/CORAL panel", NAVY, CORAL), ("example highlight NAVY/CORAL", NAVY, CORAL),
             ("example plain WHITE/NAVY panel", WHITE, NAVY), ("payoff NAVY/CORAL", NAVY, CORAL), ("pill NAVY/BLUE", NAVY, BLUE),
             ("handle BLUE/ near-black tunnel (0,26,42)", BLUE, (0, 26, 42)), ("scramble BLUE/NAVY", BLUE, NAVY)]
    for n, a, b in pairs: print(f"contrast {n}: {contrast(a, b):.2f}")
    print("sizes: num", NUM_SZ, "EN as-of", EN_SZ, "EXL_A", EXL_A.size, "EXL_B", EXL_B.size, "KO", KO1.size, KO2.size, KO3.size, "hook", HOOK[1].size, HOOK_TAIL.size)

if __name__ == "__main__":
    checks()
    if "--frames" in sys.argv:
        for ts in sys.argv[sys.argv.index("--frames") + 1].split(","):
            render(int(round(float(ts) * FPS))).save(f"{FR}/kw_{RID}_t{ts}.png")
        sys.exit()
    outp = f"{OUT}/kw_{RID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", MP3,
           "-map", "0:v", "-map", "1:a", "-af", "apad", "-t", f"{TOTAL:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-threads", "1", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", outp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(NF):
        p.stdin.write(render(i).tobytes())
        if i % 60 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait(); print("done", outp)
