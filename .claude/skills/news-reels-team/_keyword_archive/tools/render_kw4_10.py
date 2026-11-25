#!/usr/bin/env python3
"""kw v4 #10 'trade-off' - restrained PAPER CUTOUT (matte layers, soft shadows, gentle parallax).
Key image: balance scale, small room on one pan, location pin + skyline on the other, tipping slowly (no text).
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw4_10.py [--stills t1,t2,...]
Timing only from audio/words_kw_v3.json word times (min word length 0.08s guard)."""
import json, os, subprocess, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
OUT = f"{ROOT}/06_keyword_reels/v4"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
ID = "10"; W, H, FPS = 1080, 1920, 30; TAIL = 0.7
MP3 = f"{ROOT}/audio/v3/kw_{ID}.mp3"
WK = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[ID]
words = WK["words"]
for w in words:
    if w["e"] - w["s"] < 0.08: w["e"] = w["s"] + 0.08
BEATS = {b["role"]: b for b in WK["beats"]}
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc"
def font(w, s): return ImageFont.truetype(CJK % w, s, index=1)

CREAM = (241, 234, 215); CREAM2 = (231, 222, 198); SAGE = (150, 175, 140); SAGE2 = (118, 146, 114)
FOREST = (58, 92, 70); FOREST2 = (40, 68, 52); MUST = (201, 160, 66); MUSTP = (228, 205, 138)
INK = (33, 35, 30); GHOST = (176, 172, 150); HL = (232, 200, 112)
HANDLE = "지나쌤영어  @jina.ssam_english"

def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la + .05) / (lb + .05)
def sm(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def pr(t, a, b): return min(1, max(0, (t - a) / (b - a)))

# ---------------------------------------------------------------- paper helpers
_rng = np.random.default_rng(7)
def grain(w, h, amp=5):
    n = _rng.normal(0, amp, (h, w, 1)).astype(np.float32); return n
def cut(draw_fn, w, h, fill, pad=30, sh=.30, sdy=10, sblur=9, ss=2, tex=True, edge=None):
    """draw_fn(d, s) draws white-on-black mask at scale s; returns RGBA sprite with soft shadow (size w+2pad, h+2pad)."""
    W2, H2 = (w + 2 * pad) * ss, (h + 2 * pad) * ss
    m = Image.new("L", (W2, H2), 0); draw_fn(ImageDraw.Draw(m), ss, pad)
    m = m.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
    a = np.array(m).astype(np.float32) / 255
    rgb = np.zeros((h + 2 * pad, w + 2 * pad, 3), np.float32); rgb[:] = fill
    if tex: rgb += grain(w + 2 * pad, h + 2 * pad, 3.5)
    if edge is not None:  # slightly lighter rim (paper thickness)
        er = np.array(m.filter(ImageFilter.MinFilter(5))).astype(np.float32) / 255
        rim = (a - er)[..., None]; rgb = rgb * (1 - rim) + np.array(edge, np.float32) * rim
    sp = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), "RGBA")
    shm = Image.fromarray((a * 255 * sh).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sblur))
    out = Image.new("RGBA", (sp.width + 2 * sblur, sp.height + 2 * sblur + sdy), (0, 0, 0, 0))
    sh_im = Image.new("RGBA", sp.size, (20, 24, 18, 0)); sh_im.putalpha(shm)
    out.alpha_composite(sh_im, (sblur, sblur + sdy)); out.alpha_composite(sp, (sblur, sblur))
    out.info["off"] = (pad + sblur, pad + sblur)  # position of the shape's (0,0) inside sprite
    return out
def put(fr, sp, x, y, alpha=1.0):
    """place sprite so that shape origin (0,0) lands at x,y"""
    ox, oy = sp.info["off"]
    if alpha < 1:
        sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v: int(v * alpha)))
    fr.alpha_composite(sp, (int(round(x - ox)), int(round(y - oy))))
def put_c(fr, sp, cx, cy, rot=0.0, alpha=1.0):
    """place by center of the sprite image"""
    if rot: sp = sp.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1:
        sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v: int(v * alpha)))
    fr.alpha_composite(sp, (int(round(cx - sp.width / 2)), int(round(cy - sp.height / 2))))

# ---------------------------------------------------------------- background (parallax layers)
def hill(ww, hh, ytop, amp, k, ph, fill, edge, seed):
    def fn(d, s, pad):
        pts = [(pad * s, hh * s + pad * s)]
        for x in range(0, ww + 1, 12):
            y = ytop + amp * math.sin(x / ww * k * 2 * math.pi + ph) + .4 * amp * math.sin(x / ww * k * 5.3 + ph * 2)
            pts.append(((x + pad) * s, (y + pad) * s))
        pts.append(((ww + pad) * s, (hh + pad) * s)); d.polygon(pts, fill=255)
    return cut(fn, ww, hh, fill, pad=24, sh=.34, sdy=-8, sblur=12, edge=edge)
BG_W = 1180
L1 = hill(BG_W, 1000, 360, 26, 1.0, 0.5, SAGE, (170, 192, 160), 1)
L2 = hill(BG_W, 800, 270, 30, 1.3, 2.2, SAGE2, (136, 164, 130), 2)
L3 = hill(BG_W, 900, 190, 24, 0.9, 4.1, FOREST, (76, 112, 88), 3)
SUN = cut(lambda d, s, p: d.ellipse((p * s, p * s, (p + 520) * s, (p + 520) * s), fill=255), 520, 520, MUSTP, pad=30, sh=.16, sdy=8, sblur=14)
CLOUD = cut(lambda d, s, p: [d.ellipse(((p + a) * s, (p + b) * s, (p + a + c) * s, (p + b + c * .62) * s), fill=255) for a, b, c in ((0, 24, 110), (60, 0, 130), (150, 28, 100), (40, 34, 170))], 280, 110, CREAM2, pad=20, sh=.14, sdy=6, sblur=8)
BASEBG = Image.new("RGBA", (W, H), CREAM + (255,))
_g = Image.fromarray(np.clip(np.array(BASEBG)[..., :3].astype(np.float32) + grain(W, H, 2.2), 0, 255).astype(np.uint8)).convert("RGBA")
BASEBG = _g
def bg(fr, t):
    fr.alpha_composite(BASEBG)
    put_c(fr, SUN, 470 + 5 * math.sin(t * .22), 1010 + 3 * math.sin(t * .17))
    put_c(fr, CLOUD, 760 + 16 * math.sin(t * .13), 330 + 4 * math.sin(t * .2), alpha=.9)
    put_c(fr, CLOUD, 140 - 12 * math.sin(t * .11 + 1), 1180, alpha=.85)
    # hills: ox gentle drift
    for sp, y0, f, ph in ((L1, 1230, 6, 0.0), (L2, 1330, 11, 1.3), (L3, 1440, 17, 2.6)):
        ox = f * math.sin(t * .20 + ph)
        fr.alpha_composite(sp, (int(-50 + ox - sp.info["off"][0] + 24), int(y0 - 360 * (0 if sp is L1 else 0) - sp.info["off"][1] + 24 - (360 if sp is L1 else 270 if sp is L2 else 190))))

# ---------------------------------------------------------------- scale parts
PIV = (470, 930)          # pivot (x, y)
HALF = 235                # half beam length
def beam_sprite():
    w, h = HALF * 2 + 40, 26
    def fn(d, s, p): d.rounded_rectangle((p * s, p * s, (p + w) * s, (p + h) * s), radius=13 * s, fill=255)
    return cut(fn, w, h, FOREST, pad=20, sh=.34, sdy=8, sblur=7, edge=(84, 122, 98))
BEAM = beam_sprite()
STAND = cut(lambda d, s, p: (d.polygon([((p + 14) * s, (p) * s), ((p + 36) * s, (p) * s), ((p + 44) * s, (p + 400) * s), ((p + 6) * s, (p + 400) * s)], fill=255),
                            d.rounded_rectangle((p * s, (p + 392) * s, (p + 250) * s, (p + 424) * s), radius=14 * s, fill=255)), 250, 424, FOREST2, pad=24, sh=.36, sdy=10, sblur=8, edge=(70, 104, 82))
KNOB = cut(lambda d, s, p: d.ellipse((p * s, p * s, (p + 44) * s, (p + 44) * s), fill=255), 44, 44, MUST, pad=14, sh=.35, sdy=5, sblur=4)
def dish():
    w, h = 250, 44
    def fn(d, s, p): d.pieslice((p * s, (p - h) * s, (p + w) * s, (p + h) * s), 0, 180, fill=255)
    return cut(fn, w, h, FOREST2, pad=20, sh=.38, sdy=8, sblur=7, edge=(70, 104, 82))
DISH = dish()
def room():
    w, h = 150, 116
    def walls(d, s, p): d.rectangle((p * s, (p + 30) * s, (p + w) * s, (p + h) * s), fill=255)
    A = cut(walls, w, h, CREAM, pad=14, sh=.3, sdy=5, sblur=4, edge=(250, 245, 230))
    def roof(d, s, p): d.polygon([((p - 10) * s, (p + 32) * s), ((p + w / 2) * s, p * s), ((p + w + 10) * s, (p + 32) * s)], fill=255)
    B = cut(roof, w + 20, 34, SAGE2, pad=14, sh=.3, sdy=4, sblur=4)
    C = cut(lambda d, s, p: d.rectangle((p * s, p * s, (p + 40) * s, (p + 40) * s), fill=255), 40, 40, MUST, pad=10, sh=.25, sdy=3, sblur=3)
    D = cut(lambda d, s, p: d.rounded_rectangle((p * s, p * s, (p + 54) * s, (p + 24) * s), radius=6 * s, fill=255), 54, 24, SAGE2, pad=10, sh=.25, sdy=3, sblur=3)
    im = Image.new("RGBA", (260, 230), (0, 0, 0, 0))
    put(im, A, 55, 80); put(im, B, 45, 60 - 2 + 2); put(im, C, 125, 112); put(im, D, 68, 152)
    return im
ROOM = room()
def skyline():
    im = Image.new("RGBA", (260, 230), (0, 0, 0, 0))
    bl = [(0, 90, 44, SAGE2), (44, 40, 40, SAGE), (84, 70, 36, SAGE2), (120, 20, 44, SAGE), (164, 80, 40, SAGE2), (204, 56, 36, SAGE)]
    for x, top, w, c in bl:
        hh = 160 - top
        sp = cut(lambda d, s, p, w=w, hh=hh: d.rectangle((p * s, p * s, (p + w) * s, (p + hh) * s), fill=255), w, hh, c, pad=10, sh=.28, sdy=4, sblur=3)
        put(im, sp, 22 + x, 60 + top)
        for wy in range(top + 14, 150, 26):
            win = cut(lambda d, s, p: d.rectangle((p * s, p * s, (p + 9) * s, (p + 12) * s), fill=255), 9, 12, CREAM, pad=4, sh=0, sdy=0, sblur=1, tex=False)
            put(im, win, 22 + x + w / 2 - 4, 60 + wy)
    # pin
    def pin(d, s, p):
        d.ellipse((p * s, p * s, (p + 62) * s, (p + 62) * s), fill=255)
        d.polygon([((p + 8) * s, (p + 46) * s), ((p + 54) * s, (p + 46) * s), ((p + 31) * s, (p + 104) * s)], fill=255)
    P = cut(pin, 62, 104, MUST, pad=14, sh=.34, sdy=6, sblur=5, edge=(222, 186, 100))
    dot = cut(lambda d, s, p: d.ellipse((p * s, p * s, (p + 24) * s, (p + 24) * s), fill=255), 24, 24, CREAM, pad=6, sh=0, sdy=0, sblur=1, tex=False)
    put(im, P, 100, 38); put(im, dot, 119, 57)
    return im
CITY = skyline()
def tcenter(sp, cx, cy): return sp

# beam angle keyframes (deg; + = left side (room) down)
def beam_angle(t):
    KF = [(0, 7), (3.7, 7), (6.2, -5.5), (9, -5.5), (11, 4), (14.5, 4), (16.2, -3), (17.2, 0), (20.5, 0), (21.6, 7), (22.5, 7), (23.2, -7), (26.5, -4), (27.9, 0), (40, 0)]
    for (a, x), (b, y) in zip(KF, KF[1:]):
        if a <= t <= b: v = x + (y - x) * sm((t - a) / (b - a)); break
    else: v = 0
    return v + 0.5 * math.sin(t * 1.3)
def scale(fr, t):
    ang = beam_angle(t); r = math.radians(ang)
    put(fr, STAND, PIV[0] - 125 + 0, PIV[1] + 10)
    # stand: top at pivot, pole centred; STAND sprite origin is shape (0,0): pole x range 14..36 of 250 width => centre 25
    ends = []
    for sgn in (-1, 1):   # -1 left, +1 right
        ex = PIV[0] + sgn * HALF * math.cos(r); ey = PIV[1] + sgn * HALF * math.sin(-r) * -1 * -1
        ends.append((PIV[0] + sgn * HALF * math.cos(r), PIV[1] + sgn * HALF * math.sin(r) * -1))
    # + angle = left down: left end y = PIV + HALF*sin(r)
    lx, ly = PIV[0] - HALF * math.cos(r), PIV[1] + HALF * math.sin(r)
    rx, ry = PIV[0] + HALF * math.cos(r), PIV[1] - HALF * math.sin(r)
    put_c(fr, BEAM, PIV[0], PIV[1], rot=ang)
    d = ImageDraw.Draw(fr)
    for (x, y, item) in ((lx, ly, ROOM), (rx, ry, CITY)):
        dy = 190 + 4 * math.sin(t * 1.1 + x)       # string length
        px, py = x, y + dy
        for sx in (-95, 95):
            d.line([(x, y + 10), (px + sx, py - 4)], fill=FOREST2 + (255,), width=3)
        put_c(fr, DISH, px, py + 2)
        put_c(fr, item, px, py - 115 - 4 + 3)
    put_c(fr, KNOB, PIV[0], PIV[1])

# ---------------------------------------------------------------- text
X0, X1 = 70, 846
def layout(tokens, f, maxw, gap=0):
    """tokens: list of (text, idx). returns lines of [(text, idx, x, w)]"""
    lines, cur, x = [], [], 0
    sp = f.getlength(" ")
    for tx, i in tokens:
        w = f.getlength(tx)
        if cur and x + sp + w > maxw: lines.append(cur); cur, x = [], 0
        if cur: x += sp
        cur.append((tx, i, x, w)); x += w
    if cur: lines.append(cur)
    return lines
def wtimes(role):
    b = BEATS[role]; return [(words[b["first_word_idx"] + k]["s"], words[b["first_word_idx"] + k]["e"]) for k in range(b["n_words"])]
def tokens_of(role): return [(w["t"], k) for k, w in enumerate(words[BEATS[role]["first_word_idx"]:BEATS[role]["first_word_idx"] + BEATS[role]["n_words"]])]

def draw_block(base, role, t, f, y0, lh, hl=None, align="left", maxw=X1 - X0, x0=X0, color=INK):
    """word-by-word fill; whole text visible (ghost) from beat start. returns bottom y"""
    tk = tokens_of(role); tm = wtimes(role); lines = layout(tk, f, maxw)
    d = ImageDraw.Draw(base); y = y0
    for ln in lines:
        tot = ln[-1][2] + ln[-1][3]; ox = x0 + ((maxw - tot) / 2 if align == "center" else 0)
        for tx, i, x, w in ln:
            k = sm((t - tm[i][0]) / 0.22)
            col = tuple(int(GHOST[c] + (color[c] - GHOST[c]) * k) for c in range(3))
            if hl and tx.strip(".,?").lower() in hl:
                bar = Image.new("RGBA", (int(w) + 14, 30), HL + (int(255 * (.25 + .75 * k)),))
                base.alpha_composite(bar, (int(ox + x - 7), int(y + f.size * .62)))
            d.text((ox + x, y), tx, font=f, fill=col + (255,))
        y += lh
    return y

def beat_alpha(role, t, fade_in=.28):
    b = BEATS[role]; return sm((t - b["start"]) / fade_in)
def blit_alpha(fr, layer, a, dy=0):
    if a >= .999 and not dy: fr.alpha_composite(layer); return
    l = layer.copy(); l.putalpha(l.getchannel("A").point(lambda v: int(v * a))); fr.alpha_composite(l, (0, int(dy)))
def textlayer(): return Image.new("RGBA", (W, H), (0, 0, 0, 0))

F_HOOK = font("Bold", 72); F_MEAN = font("Medium", 56); F_BIG = font("Black", 168); F_SM = font("Bold", 56)
F_EN = font("Bold", 64); F_KO = font("Medium", 54); F_TAIL = font("Black", 92)
Y_TOP = 262

def scene_text(fr, t):
    # which beats are visible: current beat fades in at its start; earlier beat fades out.
    order = ["hook", "answer", "meaning", "ex1_en", "ex1_ko", "ex2_en", "ex2_ko", "tail"]
    cur = None
    for r in order:
        if t >= BEATS[r]["start"] - 1e-6: cur = r
    cur = cur or "hook"
    def layer_for(r, tt):
        L = textlayer()
        if r == "hook": draw_block(L, "hook", tt, F_HOOK, Y_TOP + 20, 108)
        elif r == "answer": draw_answer(L, tt)
        elif r == "meaning": draw_block(L, "meaning", tt, F_MEAN, Y_TOP + 20, 88)
        elif r == "ex1_en": draw_block(L, "ex1_en", tt, F_EN, Y_TOP + 40, 92, hl={"trade-off"})
        elif r == "ex1_ko": draw_block(L, "ex1_en", tt, F_EN, Y_TOP + 40, 92, hl={"trade-off"}); draw_block(L, "ex1_ko", tt, F_KO, Y_TOP + 40 + 92 * 2 + 40, 80)
        elif r == "ex2_en": draw_block(L, "ex2_en", tt, F_EN, Y_TOP + 40, 92, hl={"space", "location"})
        elif r == "ex2_ko": draw_block(L, "ex2_en", tt, F_EN, Y_TOP + 40, 92, hl={"space", "location"}); draw_block(L, "ex2_ko", tt, F_KO, Y_TOP + 40 + 92 * 2 + 40, 80)
        elif r == "tail": draw_tail(L, tt)
        return L
    i = order.index(cur)
    if i > 0:  # outgoing previous beat (fades out quickly)
        prev = order[i - 1]; k = beat_alpha(cur, t, .26)
        if k < 1:
            blit_alpha(fr, layer_for(prev, 1e9), 1 - k)
    k = beat_alpha(cur, t, .30)
    # hook is visible from frame 0 (ghost), no fade-in
    if cur == "hook": k = 1.0
    blit_alpha(fr, layer_for(cur, t), k, dy=(1 - k) * 18)

def draw_answer(L, t):
    # line 'trade-off' big; rest of sentence small above/below, exactly the spoken words
    tk = tokens_of("answer"); tm = wtimes("answer"); d = ImageDraw.Draw(L)
    def col(i):
        k = sm((t - tm[i][0]) / 0.25); return tuple(int(GHOST[c] + (INK[c] - GHOST[c]) * k) for c in range(3)), k
    # tokens: 어떤 학생은 그걸 trade-off라고 표현해요.
    pre = " ".join(x[0] for x in tk[:3]); y = Y_TOP + 40
    x = X0
    for tx, i in tk[:3]:
        c, _ = col(i); d.text((x, y), tx, font=F_SM, fill=c + (255,)); x += F_SM.getlength(tx + " ")
    c, k = col(3)
    big_w = F_BIG.getlength("trade-off"); sc = min(1.0, (X1 - X0) / big_w)
    fb = F_BIG if sc >= 1 else font("Black", int(168 * sc))
    yb = y + 100
    bw = fb.getlength("trade-off")
    bar = Image.new("RGBA", (int(bw) + 16, 56), HL + (int(255 * (.2 + .8 * k)),)); L.alpha_composite(bar, (X0 - 8, int(yb + fb.size * .66)))
    off = int((1 - k) * 14)
    d.text((X0, yb + off), "trade-off", font=fb, fill=c + (255,))
    # '라고 표현해요.' (trade-off + 라고 is one spoken token; suffix shares its time)
    c2, _ = col(3); y2 = yb + fb.size + 40
    d.text((X0, y2), "라고", font=F_SM, fill=c2 + (255,))
    xx = X0 + F_SM.getlength("라고 ")
    c3, _ = col(4); d.text((xx, y2), "표현해요.", font=F_SM, fill=c3 + (255,))

def draw_tail(L, t):
    tk = tokens_of("tail"); tm = wtimes("tail")
    lines = layout(tk, F_TAIL, X1 - X0)
    d = ImageDraw.Draw(L); y = 420
    for ln in lines:
        for tx, i, x, w in ln:
            k = sm((t - tm[i][0]) / 0.3)
            col = tuple(int(GHOST[c] + (INK[c] - GHOST[c]) * k) for c in range(3))
            if tx.strip(".").lower() == "trade-off":
                bar = Image.new("RGBA", (int(w) + 14, 34), HL + (int(255 * (.25 + .75 * k)),)); L.alpha_composite(bar, (int(X0 + x - 7), int(y + F_TAIL.size * .66)))
            d.text((X0 + x, y), tx, font=F_TAIL, fill=col + (255,))
        y += 130

# ---------------------------------------------------------------- bird, handle
LEDGE = cut(lambda d, s, p: d.rounded_rectangle((p * s, p * s, (p + 270) * s, (p + 22) * s), radius=10 * s, fill=255), 270, 22, MUST, pad=14, sh=.34, sdy=6, sblur=5)
def handle_sprite():
    f = font("Bold", 38); w = int(f.getlength(HANDLE)) + 60
    def fn(d, s, p): d.rounded_rectangle((p * s, p * s, (p + w) * s, (p + 62) * s), radius=12 * s, fill=255)
    sp = cut(fn, w, 62, CREAM, pad=12, sh=.4, sdy=4, sblur=3, tex=False)
    d = ImageDraw.Draw(sp); ox, oy = sp.info["off"]; d.text((ox + w / 2, oy + 33), HANDLE, font=f, fill=FOREST2 + (255,), anchor="mm"); return sp
HANDLE_SP = handle_sprite()
AUD = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
ENV = bird.envelope(MP3, FPS, int((AUD + TAIL) * FPS) + 5)
BCX, BBOT = 150, 1520
def bird_on(fr, t, e):
    put(fr, LEDGE, BCX - 135, BBOT - 4)
    sp = bird.sprite(float(e)); bob = 2 * math.sin(t * 2.3)
    fr.alpha_composite(sp, (int(BCX - sp.width / 2), int(BBOT - sp.height + bob)))

def render(t):
    fr = Image.new("RGBA", (W, H)); bg(fr, t)
    e = ENV[min(len(ENV) - 1, int(t * FPS))] if t < AUD else 0.0
    scale(fr, t)
    bird_on(fr, t, e)
    scene_text(fr, t)
    put_c(fr, HANDLE_SP, 540, 1588)
    return fr.convert("RGB")

def contrast_report():
    return {"ink on cream (body)": contrast(INK, CREAM), "ink on highlight mustard (hl)": contrast(INK, HL),
            "ink on pale sun disc (text never over it; check anyway)": contrast(INK, MUSTP), "ghost on cream (intentionally dim)": contrast(GHOST, CREAM),
            "forest on cream (handle)": contrast(FOREST2, CREAM)}

if __name__ == "__main__":
    if "--stills" in sys.argv:
        for ts in sys.argv[sys.argv.index("--stills") + 1].split(","):
            render(float(ts)).save(f"{FR}/kw_{ID}_t{float(ts):05.2f}.png")
        for k, v in contrast_report().items(): print(f"contrast {k}: {v:.2f}")
        sys.exit()
    total = AUD + TAIL; N = int(math.ceil(total * FPS)); outp = f"{OUT}/kw_{ID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", MP3, "-filter_complex", f"[1:a]apad=pad_dur={TAIL + 0.5}[a]", "-map", "0:v", "-map", "[a]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-threads", "2", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", outp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(N): p.stdin.write(render(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    for k, v in contrast_report().items(): print(f"contrast {k}: {v:.2f}")
    print("wrote", outp, "frames", N)
