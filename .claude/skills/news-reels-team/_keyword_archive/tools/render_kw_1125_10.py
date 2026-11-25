#!/usr/bin/env python3
"""kw 1125 #10 'trade-off' - PAPER CUTOUT + LINE ANIMATION (hand-stroked balance scale).
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw_1125_10.py [--stills t1,t2,...]
Needs numpy, Pillow, ffmpeg. Reuses tools/bird.py (sprite + mouth) and the timings in audio/words_kw.json."""
import json, os, subprocess, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
OUT = f"{ROOT}/06_keyword_reels"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
ID = "10"; W, H, FPS = 1080, 1920, 30; TAIL = 0.7
MP3 = f"{ROOT}/audio/kw_{ID}.mp3"
WK = json.load(open(f"{ROOT}/audio/words_kw.json"))[ID]
words = WK["words"]; BEATS = {b["role"]: b for b in WK["beats"]}
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc"
def font(w, s): return ImageFont.truetype(CJK % w, s, index=1)
# palette = card 2 (Court Green / Spruce Green / Tennis Yellow)
SP = (23, 65, 27); SPD = (11, 42, 16); YEL = (236, 246, 101); OFF = (246, 250, 232)
GHOST = (118, 150, 120)          # dim words on off-white paper
SHC = (3, 20, 7)
HANDLE = "지나쌤영어  @jina.ssam_english"

def lum(c):
    c = np.array(c, np.float64) / 255; c = np.where(c <= .03928, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    return float(.2126 * c[0] + .7152 * c[1] + .0722 * c[2])
def contrast(a, b):
    la, lb = lum(a), lum(b); return (max(la, lb) + .05) / (min(la, lb) + .05)
def sm(a, b, x): x = min(1, max(0, (x - a) / (b - a))); return x * x * (3 - 2 * x)
def pr(t, a, b): return min(1, max(0, (t - a) / (b - a)))
def back(p):
    c = 1.70158; p = min(1, max(0, p)); q = p - 1; return 1 + (c + 1) * q ** 3 + c * q ** 2
def wl(role):
    b = BEATS[role]; return words[b["first_word_idx"]:b["first_word_idx"] + b["n_words"]]

# ------------------------------------------------------------------ paper primitives
NOISE = np.random.default_rng(3).normal(0, 2.2, (700, 1000)).astype(np.float32)
def torn(w, h, sides="", amp=5, step=15, seed=0, corner=2):
    r = np.random.default_rng(seed); pts = []
    def j(a): return float(r.uniform(-a, a))
    n = max(2, int(w // step))
    for i in range(n + 1):
        x = w * i / n; pts.append((x + (j(corner) if i in (0, n) else 0), (j(amp) + amp) if "t" in sides else j(corner)))
    m = max(2, int(h // step))
    for i in range(1, m + 1):
        y = h * i / m; pts.append((w + (j(amp) - amp if "r" in sides else j(corner)), y))
    for i in range(n - 1, -1, -1):
        x = w * i / n; pts.append((x, h + (j(amp) - amp if "b" in sides else j(corner))))
    for i in range(m - 1, 0, -1):
        y = h * i / m; pts.append(((j(amp) + amp if "l" in sides else j(corner)), y))
    return pts

def paper(w, h, poly=None, fill=OFF, pad=26, cb=None, sh=0.5, sdy=9, sblur=7, seed=1, tex=True):
    S = 2; pw, ph = w + 2 * pad, h + 2 * pad
    poly = poly or torn(w, h, "", 0, 40, seed, 3)
    mk = Image.new("L", (pw * S, ph * S), 0)
    ImageDraw.Draw(mk).polygon([((x + pad) * S, (y + pad) * S) for x, y in poly], fill=255)
    mk = mk.resize((pw, ph), Image.LANCZOS)
    shd = ImageChops.offset(mk.filter(ImageFilter.GaussianBlur(sblur)), 3, sdy).point(lambda v: int(v * sh))
    img = Image.new("RGBA", (pw, ph), SHC + (0,)); img.putalpha(shd)
    col = np.zeros((ph, pw, 3), np.float32) + np.array(fill, np.float32)
    if tex: col += NOISE[:ph, :pw, None] * (0.8 if (w * h) > 20000 else 0.0)
    body = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert("RGBA"); body.putalpha(mk)
    img.alpha_composite(body)
    if cb: cb(ImageDraw.Draw(img), pad)
    return img

def place(fr, sp, cx, cy, rot=0.0, sc=1.0, alpha=1.0):
    im = sp
    if sc != 1.0: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    if abs(rot) > 0.01: im = im.rotate(-rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1.0: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + im.width), min(H, y + im.height)
    if x1 <= x0 or y1 <= y0: return
    fr.alpha_composite(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))

def text_c(d, xy, s, f, fill): d.text(xy, s, font=f, fill=fill + (255,), anchor="mm")

# ------------------------------------------------------------------ hand-drawn strokes
def stroke_items(layer_wh, items, org=(0, 0), ss=2):
    """items: (pts, frac, width, colour). draws first `frac` of each polyline with a gentle hand wobble, returns RGBA."""
    lw, lh = layer_wh; im = Image.new("RGBA", (lw * ss, lh * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for pts, frac, wd, col in items:
        if frac <= 0.001 or len(pts) < 2: continue
        P = np.array(pts, np.float64); seg = np.hypot(*np.diff(P, axis=0).T); tot = seg.sum()
        if tot < 1: continue
        n = max(2, int(tot / 5)); s = np.linspace(0, tot * min(1, frac), n)
        cum = np.concatenate([[0], np.cumsum(seg)]); x = np.interp(s, cum, P[:, 0]); y = np.interp(s, cum, P[:, 1])
        ph = (P[0, 0] * .13 + P[0, 1] * .07)
        x = x + 1.7 * np.sin(s * 0.045 + ph); y = y + 1.7 * np.cos(s * 0.037 + ph * 1.7)
        xy = [((a - org[0]) * ss, (b - org[1]) * ss) for a, b in zip(x, y)]
        d.line(xy, fill=col + (255,), width=int(wd * ss), joint="curve")
        r = wd * ss / 2
        for a, b in (xy[0], xy[-1]):
            d.ellipse((a - r, b - r, a + r, b + r), fill=col + (255,))
    return im.resize((lw, lh), Image.LANCZOS)

def bez(p0, p1, p2, n=24):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]) for u in np.linspace(0, 1, n)]
def arrow(curve, t_pr, wd, col, hl=34):
    """curve points, progress 0..1 -> items (curve + two head strokes drawn at the end)"""
    a = np.array(curve[-2]); b = np.array(curve[-1]); v = (b - a) / (np.hypot(*(b - a)) + 1e-6); n = np.array([-v[1], v[0]])
    h1 = [tuple(b), tuple(b - v * hl + n * hl * .6)]; h2 = [tuple(b), tuple(b - v * hl - n * hl * .6)]
    return [(curve, min(1, t_pr / 0.8), wd, col), (h1, pr(t_pr, .82, .92), wd, col), (h2, pr(t_pr, .9, 1.0), wd, col)]

# ------------------------------------------------------------------ background: paper layers + Paris mansard roofs
def periodic_noise(n, amp, seed):
    r = np.random.default_rng(seed); v = r.uniform(-amp, amp, n); v[-1] = v[0]; return v
def wave_layer(base, a1, k1, a2, k2, ph, fill, rim, seed, ytop):
    ww = 2160; xs = np.arange(0, 1081, 12); nz = periodic_noise(len(xs), 2.6, seed)
    ys = base + a1 * np.sin(2 * np.pi * k1 * xs / 1080 + ph) + a2 * np.sin(2 * np.pi * k2 * xs / 1080 + ph * 2.1) + nz
    return build_layer(xs, ys, fill, rim, ytop, ww)
def build_layer(xs, ys, fill, rim, ytop, ww=2160, shadow=0.55):
    hh = H - ytop; S = 1
    def poly(dy):
        pts = []
        for rep in (0, 1):
            pts += [(x + rep * 1080, y + dy - ytop) for x, y in zip(xs, ys)]
        pts += [(ww, hh), (0, hh)]; return pts
    mk = Image.new("L", (ww, hh), 0); ImageDraw.Draw(mk).polygon(poly(0), fill=255)
    rk = Image.new("L", (ww, hh), 0); ImageDraw.Draw(rk).polygon(poly(-4), fill=255)
    shd = ImageChops.offset(rk.filter(ImageFilter.GaussianBlur(12)), 0, -10).point(lambda v: int(v * shadow))
    im = Image.new("RGBA", (ww, hh), SHC + (0,)); im.putalpha(shd)
    r_ = Image.new("RGBA", (ww, hh), rim + (255,)); r_.putalpha(rk); im.alpha_composite(r_)
    b_ = Image.new("RGBA", (ww, hh), fill + (255,)); b_.putalpha(mk); im.alpha_composite(b_)
    return im, ytop
def roof_layer(rb, fill, rim, seed, ytop, bw=270, lit=0.5):
    r = np.random.default_rng(seed); xs = []; ys = []
    nb = 1080 // bw
    for b in range(nb):
        x0 = b * bw; top = rb + r.uniform(-40, 30); sl = r.uniform(.8, 1.2)
        prof = [(x0, top + 120), (x0, top + 40 * sl), (x0 + 34, top - 10 * sl), (x0 + bw * .5, top - 48 * sl), (x0 + bw - 34, top - 10 * sl), (x0 + bw - 1, top + 40 * sl), (x0 + bw - 1, top + 120)]
        if r.uniform() < .7:  # chimney
            cx = x0 + r.uniform(60, bw - 90); prof = prof[:3] + [(cx, top - 6), (cx, top - 70), (cx + 28, top - 70), (cx + 28, top - 30)] + prof[3:]
            prof.sort(key=lambda p: p[0])
        for p in prof: xs.append(p[0]); ys.append(p[1])
    xs.append(1080); ys.append(ys[0])
    im, yt = build_layer(np.array(xs), np.array(ys), fill, rim, ytop, shadow=0.6)
    d = ImageDraw.Draw(im)
    for b in range(nb * 2):   # lit dormer windows (cut yellow paper)
        x0 = (b % nb) * bw + (b // nb) * 1080
        if r.uniform() < lit:
            wx = x0 + bw * .5 - 17 + r.uniform(-30, 30); wy = rb - ytop + r.uniform(20, 70)
            d.rectangle((wx, wy, wx + 34, wy + 40), fill=YEL + (255,)); d.line((wx + 17, wy, wx + 17, wy + 40), fill=fill + (255,), width=3)
    return im, yt
BG = [wave_layer(430, 70, 1, 22, 3, 0.4, (30, 84, 36), (60, 118, 62), 11, 300) + (7,),
      wave_layer(820, 60, 2, 20, 4, 1.7, (24, 72, 31), (52, 104, 56), 12, 650) + (13,),
      roof_layer(1370, (15, 52, 21), (36, 84, 42), 21, 1200, 270, .55) + (22,),
      roof_layer(1500, (9, 36, 14), (26, 66, 32), 22, 1330, 360, .35) + (36,)]
def bg(fr, t):
    fr.paste(Image.new("RGBA", (W, H), SP + (255,)))
    for im, yt, spd in BG:
        o = int((spd * t) % 1080); fr.alpha_composite(im.crop((o, 0, o + W, im.height)), (0, yt))
SCRAPS = []
for i in range(12):
    r = np.random.default_rng(100 + i); s = int(r.uniform(22, 44))
    kind = r.integers(0, 3); poly = [(0, 0), (s, 4), (s - 5, s), (3, s - 6)] if kind == 0 else ([(0, s), (s / 2, 0), (s, s)] if kind == 1 else [(0, 0), (s, 0), (s, s * .6), (0, s * .6)])
    SCRAPS.append((paper(s, s, poly, fill=[YEL, OFF, (120, 170, 110)][int(r.integers(0, 3))], pad=10, sh=.4, sdy=4, sblur=3, tex=False), r.uniform(0, 1080), r.uniform(220, 1250), r.uniform(10, 26), r.uniform(-60, 60)))
def scraps(fr, t):
    for sp, x0, y0, vy, vr in SCRAPS:
        x = (x0 + 24 * math.sin(t * .7 + y0)) % 1000; y = 230 + ((y0 - 230 - vy * t) % 1050)
        place(fr, sp, x + 40, y, rot=vr * t * .6 + y0, alpha=.9)

# ------------------------------------------------------------------ persistent elements
def pill_sprite():
    f = font("Bold", 32); s = "NEWS ENGLISH · CNN"; w = int(f.getlength(s)) + 52
    return paper(w, 52, torn(w, 52, "", 0, 30, 5, 2), fill=YEL, pad=14, sh=.45, sdy=5, sblur=4, cb=lambda d, p: text_c(d, (p + w / 2, p + 27), s, f, SP))
PILL = pill_sprite()
def handle(fr):
    f = font("Bold", 38); w = int(f.getlength(HANDLE)) + 60
    sp = paper(w, 62, fill=OFF, pad=12, sh=.4, sdy=4, sblur=3, tex=False, poly=torn(w, 62, "", 0, 40, 9, 2), cb=lambda d, p: text_c(d, (p + w / 2, p + 33), HANDLE, f, SP))
    return sp
HANDLE_SP = handle(None)
LEDGE = paper(330, 78, torn(330, 78, "t", 4, 22, 31, 2), fill=YEL, pad=18, sh=.55, sdy=8, sblur=6)
AUD = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
ENV = bird.envelope(MP3, FPS, int((AUD + TAIL) * FPS) + 5)
def bird_on_roof(fr, t, env):
    place(fr, LEDGE, 660, 1500)
    sp = bird.sprite(float(env)); bob = 3 * math.sin(t * 3.1)
    fr.alpha_composite(sp, (int(660 - sp.width / 2), int(1478 - sp.height + bob)))

# ------------------------------------------------------------------ word-by-word paper text
def layout(lines, f, gap):
    """lines: list of list of tokens (text, hl_text or None). returns per-line widths and token x offsets (relative to line centre)"""
    out = []
    for toks in lines:
        ws = [f.getlength(tk[0]) for tk in toks]; tot = sum(ws) + gap * (len(toks) - 1); x = -tot / 2; xs = []
        for w_ in ws: xs.append(x); x += w_ + gap
        out.append((xs, ws, tot))
    return out
def word_state(t, a, b): return 0 if t < a else (1 if t < b else 2)   # ghost / active / past
def draw_words(base, lines, times, f, t, lh, cx, cy0, pad, tabpad=14, hl_always=None, hl_t0=None):
    """lines tokens: (text, hltext|None). times: parallel list (start,end). draws onto copy of base."""
    im = base.copy(); d = ImageDraw.Draw(im); L = layout(lines, f, int(f.size * .26))
    k = 0
    for li, (toks, (xs, ws, tot)) in enumerate(zip(lines, L)):
        y = cy0 + li * lh
        for tk, x, w_ in zip(toks, xs, ws):
            a, b = times[k]; k += 1; st = word_state(t, a, b); xx = cx + x
            hl = tk[1]
            if hl:     # highlight = yellow paper tab that slides in at its word start
                hw = f.getlength(hl); p = sm(0, .22, t - hl_t0) if t >= hl_t0 else 0
                if p > 0:
                    tw = (hw + 2 * tabpad) * p; poly = [(xx - tabpad, y - lh * .5 + 12), (xx - tabpad + tw, y - lh * .5 + 8), (xx - tabpad + tw + 2, y + lh * .5 - 8), (xx - tabpad - 1, y + lh * .5 - 4)]
                    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([(px + 3, py + 7) for px, py in poly], fill=SHC + (90,))
                    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4))); d = ImageDraw.Draw(im); d.polygon(poly, fill=YEL + (255,))
            elif st == 1:   # active: yellow marker strip behind the word
                poly = [(xx - 10, y - lh * .5 + 18), (xx + w_ + 10, y - lh * .5 + 14), (xx + w_ + 12, y + lh * .5 - 14), (xx - 12, y + lh * .5 - 10)]
                d.polygon(poly, fill=YEL + (255,))
            col = GHOST if st == 0 else SP
            dy = -5 if st == 1 else 0
            d.text((xx, y + dy), tk[0], font=f, fill=col + (255,), anchor="lm")
    return im

# ------------------------------------------------------------------ SCENE: hook (0 - 2.92)
HK = wl("hook")
HOOK_TOK = [[("이", None), ("좁은", None), ("방,", None)], [("희생일까요?", None)]]
HOOK_T = [(HK[0]["s"], HK[1]["s"]), (HK[1]["s"], HK[2]["s"]), (HK[2]["s"], HK[5]["s"]), (HK[5]["s"], BEATS["hook"]["end"] + .2)]
F_HOOK = font("Black", 132)
STRIP_W, STRIP_H = 788, 400
STRIP = paper(STRIP_W, STRIP_H, torn(STRIP_W, STRIP_H, "b", 6, 17, 41, 3), fill=OFF, pad=30)
Q_SP = paper(250, 380, [(0, 0), (1, 0), (1, 1)], fill=YEL, pad=20, sh=0)  # placeholder (replaced below)
def mk_q():
    f = font("Black", 440); pad = 40; im = Image.new("RGBA", (330, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((167, 266), "?", font=f, fill=SHC + (170,), anchor="mm", stroke_width=18, stroke_fill=SHC + (170,))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    d.text((160, 254), "?", font=f, fill=YEL + (255,), anchor="mm", stroke_width=15, stroke_fill=OFF + (255,))
    return im
Q_SP = mk_q()
def mk_room():
    w, h = 420, 340; pad = 26
    def cb(d, p):
        # back building (darker paper), facade windows, mansard roof, dormer
        d.polygon([(p + 40, p + 118), (p + 380, p + 118), (p + 380, p + 330), (p + 40, p + 330)], fill=(214, 226, 190, 255))
        for i in range(3):
            d.rectangle((p + 70 + i * 100, p + 240, p + 120 + i * 100, p + 300), fill=SP + (255,))
        d.polygon([(p + 10, p + 130), (p + 80, p + 30), (p + 340, p + 30), (p + 410, p + 130)], fill=YEL + (255,))
        d.polygon([(p + 80, p + 30), (p + 340, p + 30), (p + 322, p + 8), (p + 98, p + 8)], fill=(200, 214, 84, 255))
        d.rectangle((p + 268, p - 6, p + 296, p + 22), fill=(170, 186, 70, 255))
        d.rectangle((p + 150, p + 52, p + 270, p + 122), fill=SP + (255,)); d.rectangle((p + 158, p + 60, p + 262, p + 118), fill=OFF + (255,))
        d.line((p + 210, p + 60, p + 210, p + 118), fill=SP + (255,), width=5); d.line((p + 158, p + 90, p + 262, p + 90), fill=SP + (255,), width=5)
        d.rectangle((p + 176, p + 74, p + 198, p + 112), fill=SPD + (255,))   # tiny bed shape in the window
    poly = [(40, 118), (10, 130), (80, 30), (340, 30), (410, 130), (380, 118), (380, 330), (40, 330)]
    return paper(w, h, poly, fill=(214, 226, 190), pad=pad, cb=cb, tex=False)
ROOM = mk_room()
def scene_hook(fr, t, env):
    pop = 1 + .03 * math.exp(-t * 8) ; rot = -1.5 + 1.0 * math.sin(t * 2.2) + 2.5 * math.exp(-t * 7)
    st = draw_words(STRIP, HOOK_TOK, HOOK_T, F_HOOK, t, 168, STRIP_W / 2 + 30 + 0, 30 + 112, 30)
    if t >= 2.92:
        k = pr(t, 2.92, 3.3); place(fr, st, 456, 545 - 700 * k * k, rot - 14 * k, 1)
    else:
        place(fr, st, 456, 545, rot, pop)
    # '?' cut-out
    qp = back(pr(t, 0, .45)); qs = .55 + .45 * qp; qs = qs if t < 2.92 else qs * (1 + .2 * pr(t, 2.92, 3.2))
    if t < 3.3: place(fr, Q_SP, 650, 905 + 8 * math.sin(t * 3.2), 7 + 5 * math.sin(t * 2.4), qs, alpha=1 - pr(t, 2.92, 3.3))
    # room (squeezed width arrows drawn by stroke)
    rk = back(pr(t, 0, .5));
    if t < 3.3:
        place(fr, ROOM, 268, 950 + 7 * math.sin(t * 2.0), -2 + 1.5 * math.sin(t * 1.6), .62 + .38 * rk, alpha=1 - pr(t, 2.92, 3.3))
        sq = sm(1.3, 2.7, t); half = 190 - 70 * sq; d0 = pr(t, .2, 1.0)
        x0, x1 = 268 - half, 268 + half; y = 1175
        items = [([(268, y), (x0, y)], d0, 8, YEL), ([(268, y), (x1, y)], d0, 8, YEL),
                 ([(x0 + 28, y - 18), (x0, y), (x0 + 28, y + 18)], pr(d0, .8, 1), 8, YEL), ([(x1 - 28, y - 18), (x1, y), (x1 - 28, y + 18)], pr(d0, .8, 1), 8, YEL)]
        lay = stroke_items((560, 120), items, org=(0, 1115)); lay.putalpha(lay.getchannel("A").point(lambda v: int(v * (1 - pr(t, 2.92, 3.3)))))
        fr.alpha_composite(lay, (0, 1115))

# ------------------------------------------------------------------ balance scale (strokes)
LBEAM = 285; HANG = 210; PAN = 92
def rot_pt(cx, cy, u, v, a):
    c, s = math.cos(a), math.sin(a); return (cx + u * c - v * s, cy + u * s + v * c)
def scale_items(cx, cy, S, a, p):
    """p: dict of progress (post, base, beam, strings, bowl). local coords scaled by S, angle a (rad, clockwise)"""
    col = OFF; items = []
    Lb = LBEAM * S; hg = HANG * S; pw = PAN * S
    items.append(([(cx, cy), (cx, cy + 540 * S)], p["post"], 12 * S + 2, col))
    items.append(([(cx - 120 * S, cy + 545 * S), (cx + 120 * S, cy + 545 * S)], p["base"], 12 * S + 2, col))
    items.append(([(cx - 70 * S, cy + 545 * S), (cx - 20 * S, cy + 330 * S)] , 0, 1, col))
    l = rot_pt(cx, cy, -Lb, 0, a); r = rot_pt(cx, cy, Lb, 0, a)
    items.append(([l, (cx, cy), r], p["beam"], 13 * S + 2, col))
    for e in (l, r):
        py = e[1] + hg
        items.append(([e, (e[0] - pw, py)], p["strings"], 7 * S + 2, col)); items.append(([e, (e[0] + pw, py)], p["strings"], 7 * S + 2, col))
        bowl = [(e[0] + pw * math.cos(math.pi - th), py + 40 * S * math.sin(th)) for th in np.linspace(0, math.pi, 22)]
        items.append((bowl, p["bowl"], 10 * S + 2, col))
    items.append(([(cx - 2, cy), (cx + 2, cy)], p["beam"], 34 * S, col))
    return items, l, r
def beam_angle(t, t_hit):
    if t < t_hit:
        return math.radians(1.1 * math.sin(3.4 * (t - 3.6)) * sm(4.4, 5.0, t))
    tau = t - t_hit
    return math.radians(5 * (1 - math.exp(-2.6 * tau) * math.cos(8.5 * tau)))

def mk_tag(text, w, h, fill, f):
    poly = [(0, h * .5), (h * .34, 0), (w, 2), (w - 2, h - 1), (h * .34, h)]
    def cb(d, p):
        d.ellipse((p + h * .27 - 8, p + h * .5 - 8, p + h * .27 + 8, p + h * .5 + 8), fill=SPD + (255,))
        text_c(d, (p + h * .34 + (w - h * .34) / 2, p + h / 2 + 2), text, f, SP)
    return paper(w, h, poly, fill=fill, cb=cb, pad=22, sh=.55)
TAG_SPACE = mk_tag("SPACE", 196, 98, YEL, font("Black", 44))
def mk_pin():
    w, h = 200, 200; pad = 22; f = font("Black", 31)
    def cb(d, p):
        d.ellipse((p + 100 - 58, p + 8, p + 100 + 58, p + 124), fill=OFF + (255,))
        d.polygon([(p + 100 - 50, p + 82), (p + 100 + 50, p + 82), (p + 100, p + 150)], fill=OFF + (255,))
        d.ellipse((p + 100 - 22, p + 38, p + 100 + 22, p + 82), fill=SP + (255,))
        d.polygon([(p + 4, p + 150), (p + 196, p + 146), (p + 198, p + 198), (p + 2, p + 196)], fill=YEL + (255,))
        text_c(d, (p + 100, p + 175), "LOCATION", f, SP)
    sp = paper(w, h, [(100, 0), (160, 30), (160, 120), (200, 150), (200, h), (0, h), (0, 150), (40, 120), (40, 30)], fill=OFF, pad=pad, cb=cb, tex=False)
    return sp
PIN = mk_pin()
TILE_H = 106; TILE_W = 72
def mk_tile(ch, i, big=False):
    f = font("Black", 150 if big else 88); r = np.random.default_rng(i + (50 if big else 0))
    wd = (122 if big else TILE_W) if ch != "-" else (70 if big else 46); ht = 176 if big else TILE_H
    poly = [(r.uniform(0, 3), r.uniform(0, 3)), (wd - r.uniform(0, 3), r.uniform(0, 4)), (wd - r.uniform(0, 3), ht - r.uniform(0, 3)), (r.uniform(0, 3), ht - r.uniform(0, 3))]
    fill = YEL if i % 2 == 0 else OFF
    return paper(wd, ht, poly, fill=fill, pad=20, sh=.55, cb=lambda d, p: text_c(d, (p + wd / 2, p + ht / 2 + (4 if big else 3)), ch, f, SP)), wd
LETTERS = "trade-off"
TILES = [mk_tile(c, i) for i, c in enumerate(LETTERS)]
TILES_BIG = [mk_tile(c, i, True) for i, c in enumerate(LETTERS)]
QSLOT = None
def mk_qslot():
    im = Image.new("RGBA", (120, 140), (0, 0, 0, 0)); ImageDraw.Draw(im).text((60, 70), "?", font=font("Black", 104), fill=YEL + (255,), anchor="mm")
    return im
QSLOT = mk_qslot()
TM = wl("term"); ANS_T = TM[3]["s"]   # 'trade-off.' start (5.36)
SCX, SCY = 456, 600
F_TS = font("Black", 60); TS_TOK = [[("학생은", None), ("아니래요.", None), ("답은,", None)]]
TS_T = [(TM[0]["s"], TM[1]["s"]), (TM[1]["s"], TM[2]["s"]), (TM[2]["s"], TM[2]["e"])]
TS_W = int(layout(TS_TOK, F_TS, int(F_TS.size * .26))[0][2]) + 70
TS_CARD = paper(TS_W, 110, torn(TS_W, 110, "b", 4, 17, 83, 3), fill=OFF, pad=30)
def scene_term(fr, t, env):
    lt = t - BEATS["term"]["start"]
    if 3.3 <= t < 5.6:
        k = back(pr(t, 3.3, 3.65)); ex = pr(t, 5.3, 5.6)
        cd = draw_words(TS_CARD, TS_TOK, TS_T, F_TS, t, 110, TS_W / 2 + 30, 30 + 55, 30)
        place(fr, cd, 456, 378 - (1 - k) * 200 - 500 * ex * ex, -1.2 + 1.5 * (1 - k))
    p = {"post": pr(t, 2.95, 3.5), "base": pr(t, 3.4, 3.75), "beam": pr(t, 3.65, 4.2), "strings": pr(t, 4.1, 4.55), "bowl": pr(t, 4.4, 4.8)}
    a = beam_angle(t, ANS_T)
    items, l, r = scale_items(SCX, SCY, 1.0, a, p)
    # dashed answer slot riding the beam (hand drawn)
    if t < ANS_T + .05:
        sw, shh = 700, 116; per = 2 * (sw + shh); dash = 34; gapd = 22; prog = pr(t, 3.0, 4.2) * per
        corners = [(-sw / 2, -92 - shh / 2), (sw / 2, -92 - shh / 2), (sw / 2, -92 + shh / 2), (-sw / 2, -92 + shh / 2), (-sw / 2, -92 - shh / 2)]
        s0 = 0
        for c0, c1 in zip(corners[:-1], corners[1:]):
            ln = math.hypot(c1[0] - c0[0], c1[1] - c0[1]); k = 0
            while k < ln:
                e = min(ln, k + dash)
                if s0 + k < prog:
                    u0 = k / ln; u1 = e / ln
                    q0 = rot_pt(SCX, SCY, c0[0] + (c1[0] - c0[0]) * u0, c0[1] + (c1[1] - c0[1]) * u0, a); q1 = rot_pt(SCX, SCY, c0[0] + (c1[0] - c0[0]) * u1, c0[1] + (c1[1] - c0[1]) * u1, a)
                    items.append(([q0, q1], 1, 7, YEL))
                k += dash + gapd
            s0 += ln
    org = (0, 300); lay = stroke_items((900, 1000), items, org=org)
    fr.alpha_composite(lay, org)
    if t < ANS_T + .05 and t > 3.3:
        q = rot_pt(SCX, SCY, 0, -92, a); place(fr, QSLOT, q[0], q[1] + 3 * math.sin(t * 5), math.degrees(a) + 4 * math.sin(t * 3), back(pr(t, 3.4, 3.9)) * (1 - pr(t, ANS_T - .05, ANS_T + .05)))
    # tags land in the pans
    for sp, e, t0, anc in ((TAG_SPACE, l, 4.55, 49), (PIN, r, 4.8, 100)):
        k = pr(t, t0, t0 + .35)
        if k <= 0: continue
        drop = (1 - k) ** 2 * -240 if k < 1 else 0
        place(fr, sp, e[0], e[1] + HANG + 8 - sp.height / 2 + 22 + drop, -math.degrees(a) * .35 + 3 * math.sin(t * 2.5 + e[0]) * (1 if k >= 1 else 0))
    # answer letters drop onto the beam
    x = -(sum(w_ for _, w_ in TILES) + 6 * (len(TILES) - 1)) / 2
    for i, ((sp, w_), ch) in enumerate(zip(TILES, LETTERS)):
        u = x + w_ / 2; x += w_ + 6
        tau = t - (ANS_T + .12 * i)
        if tau < 0: continue
        if tau < .28: off = -(420 - 5350 * tau * tau); rr = (1 - tau / .28) * (14 if i % 2 else -14)
        else: t2 = tau - .28; off = -16 * math.exp(-7 * t2) * abs(math.sin(14 * t2)); rr = 0
        q = rot_pt(SCX, SCY, u, -(8 + TILE_H / 2 + 3), a)
        place(fr, sp, q[0], q[1] + off, math.degrees(a) + rr + (1.5 if i % 2 else -1.5))

# ------------------------------------------------------------------ SCENE: meaning (6.8 - 10.0)
ME = wl("meaning"); MT = BEATS["meaning"]["start"]
TAG_A = mk_tag("절충", 400, 170, YEL, font("Black", 120)); TAG_B = mk_tag("맞교환", 500, 170, OFF, font("Black", 120))
DOT = paper(46, 46, [(23 + 23 * math.cos(i / 10 * 2 * math.pi), 23 + 23 * math.sin(i / 10 * 2 * math.pi)) for i in range(10)], fill=YEL, pad=12, sh=.5, sdy=5, sblur=4, tex=False)
def scene_meaning(fr, t, env):
    YA, YB = 500, 840; sw = sm(8.84, 9.4, t)
    ta, tb = ME[0]["s"], ME[1]["s"]
    # tags swap places along bulging paths
    ay = YA + (YB - YA) * sw; ax = 456 - 190 * math.sin(math.pi * sw)
    by = YB + (YA - YB) * sw; bx = 456 + 150 * math.sin(math.pi * sw)
    ssc = 1 - .25 * math.sin(math.pi * sw)
    ka = back(pr(t, ta, ta + .35)); kb = back(pr(t, tb, tb + .35))
    if t >= tb: place(fr, DOT, 456, 670, t * 90, back(pr(t, tb + .1, tb + .45)))
    if t >= ta: place(fr, TAG_A, ax, ay - (1 - ka) * 260, -4 + 10 * math.sin(math.pi * sw) + 1.5 * math.sin(t * 2.2), ssc)
    if t >= tb: place(fr, TAG_B, bx, by - (1 - kb) * 300, 3 - 9 * math.sin(math.pi * sw) + 1.5 * math.sin(t * 2.6), ssc)
    p1 = pr(t, 8.0, 8.7)
    if p1 > 0:
        cl = bez((150, 450), (70, 670), (150, 890)); cr = bez((775, 890), (860, 670), (775, 450))
        items = arrow(cl, p1, 11, YEL) + arrow(cr, p1, 11, OFF)
        org = (0, 380); lay = stroke_items((900, 600), items, org=org); fr.alpha_composite(lay, org)

# ------------------------------------------------------------------ SCENE: example EN / KO
EX = wl("example_en"); KO = wl("example_ko")
F_EN = font("Black", 90)
EN_TOK = [[("Every", None), ("choice", None), ("is", None)], [("a", None), ("trade-off.", "trade-off")]]
EN_T = [(EX[0]["s"], EX[1]["s"]), (EX[1]["s"], EX[2]["s"]), (EX[2]["s"], EX[3]["s"]), (EX[3]["s"], EX[4]["s"]), (EX[4]["s"], BEATS["example_en"]["end"])]
CW, CH = 788, 420
CARD = paper(CW, CH, torn(CW, CH, "b", 7, 16, 61, 3), fill=OFF, pad=30)
EXLAB = mk_tag("EXAMPLE", 270, 66, YEL, font("Black", 34))
KOW, KOH = 740, 400
F_KO = font("Black", 104)
KO_TOK = [[("모든", None), ("선택은", None)], [("절충이다.", None)]]
KO_T = [(KO[0]["s"], KO[1]["s"]), (KO[1]["s"], KO[2]["s"]), (KO[2]["s"], BEATS["example_ko"]["end"])]
KCARD = paper(KOW, KOH, torn(KOW, KOH, "t", 7, 16, 71, 3), fill=YEL, pad=30)
def draw_ko(base, t):
    im = base.copy(); d = ImageDraw.Draw(im); L = layout(KO_TOK, F_KO, 28); k = 0
    for li, (toks, (xs, ws, tot)) in enumerate(zip(KO_TOK, L)):
        y = 30 + 115 + li * 140
        for tk, x, w_ in zip(toks, xs, ws):
            a, b = KO_T[k]; k += 1; st = word_state(t, a, b); xx = 30 + KOW / 2 + x
            if st == 1: d.polygon([(xx - 8, y - 56), (xx + w_ + 8, y - 60), (xx + w_ + 10, y + 52), (xx - 10, y + 56)], fill=OFF + (255,))
            d.text((xx, y + (-5 if st == 1 else 0)), tk[0], font=F_KO, fill=(SP if st else (62, 100, 64)) + (255,), anchor="lm")
    return im
def scene_en(fr, t, env, ko=False):
    t0 = BEATS["example_en"]["start"]; t1 = BEATS["example_ko"]["start"]
    k = back(pr(t, t0, t0 + .4)); sl = 0 if not ko else sm(t1, t1 + .35, t)
    card = draw_words(CARD, EN_TOK, EN_T, F_EN, t, 150, CW / 2 + 30, 30 + 135, 30, hl_t0=EX[4]["s"])
    cy = 560 + (505 - 560) * sl - (1 - k) * 700; sc = 1 - .2 * sl
    place(fr, card, 456, cy, -1.5 + 2.5 * sl, sc)
    place(fr, EXLAB, 200 - 40 * sl, cy - CH * .5 * sc - 6 + 8 * math.sin(t * 2), -5, sc)
    if not ko:   # mini hand-drawn scale that tilts when 'trade-off' is spoken
        p = {"post": pr(t, 10.15, 10.55), "base": pr(t, 10.5, 10.7), "beam": pr(t, 10.6, 10.95), "strings": pr(t, 10.9, 11.15), "bowl": pr(t, 11.1, 11.3)}
        a = beam_angle(t, EX[4]["s"]); items, l, r = scale_items(456, 900, .55, a, p)
        org = (200, 760); lay = stroke_items((520, 520), items, org=org); fr.alpha_composite(lay, org)
        for sp, e, dx in ((TAG_SPACE, l, 0), (PIN, r, 0)):
            kk = pr(t, 11.2, 11.5)
            if kk > 0: place(fr, sp, e[0], e[1] + HANG * .55 - 8 - (sp.height * .55) / 2 + 22 + (1 - kk) ** 2 * -150, -math.degrees(a) * .3, .5 if sp is PIN else .55)
    else:
        kk = back(pr(t, t1, t1 + .4)); kc = draw_ko(KCARD, t)
        place(fr, kc, 456, 900 + (1 - kk) * 700, 1.5 - 1 * math.sin(t * 1.5))

# ------------------------------------------------------------------ SCENE: payoff (expression once, 2 examples, save)
PO = wl("payoff"); PB = BEATS["payoff"]; PT = PB["start"]
EXPR_S, EXPR_E, E1S, E1E, E2S, E2E, SAVE_S = PB["expr_start"], PB["expr_end"], PB["ex1_start"], PB["ex1_end"], PB["ex2_start"], PB["ex2_end"], PB["save_start"]
def seg(a, b): return [w for w in words if a - 1e-6 <= w["s"] <= b + 1e-6]
W1, W2 = seg(E1S, E1E), seg(E2S, E2E)
assert " ".join(w["t"] for w in W1) == PB["ex1_text"] and " ".join(w["t"] for w in W2) == PB["ex2_text"], "on-screen must equal spoken"
E1_TOK = [[("Every", None), ("big", None), ("choice", None)], [("has", None), ("a", None), ("trade-off.", "trade-off")]]
E2_TOK = [[("Small", None), ("space,", None)], [("low", None), ("rent.", None)], [("That's", None), ("the", None), ("trade-off.", "trade-off")]]
def mk_times(W, endt): return [(W[i]["s"], W[i + 1]["s"] if i + 1 < len(W) else endt) for i in range(len(W))]
E1_T = mk_times(W1, E1E); E2_T = mk_times(W2, E2E)
# one font size so the widest line fits in the card (<= 700px)
def widest(f): return max(max(l[2] for l in layout(T, f, int(f.size * .26))) for T in (E1_TOK, E2_TOK))
FS = 84
while widest(font("Black", FS)) > 700: FS -= 2
F_PE = font("Black", FS); PLH = int(FS * 1.5)
PCW = 788
PC1 = paper(PCW, 2 * PLH + 50, torn(PCW, 2 * PLH + 50, "b", 7, 16, 91, 3), fill=OFF, pad=30)
PC2 = paper(PCW, 3 * PLH + 50, torn(PCW, 3 * PLH + 50, "b", 7, 16, 92, 3), fill=OFF, pad=30)
TAG_RENT = mk_tag("RENT", 196, 98, OFF, font("Black", 44))
TAB = paper(520, 130, [(0, 4), (500, 0), (520, 65), (500, 130), (0, 126), (20, 65)], fill=YEL, pad=24, cb=lambda d, p: text_c(d, (p + 280, p + 68), "저장해 두기", font("Black", 66), SP))
BM_PTS = [(0, 0), (92, 0), (92, 148), (46, 108), (0, 148), (0, 0)]
PHIT = [(W1[5]["s"], 5.0), (W2[-1]["s"], -5.0)]   # trade-off words: beam tips one way, then the other
def pay_angle(t):
    a = math.radians(1.1 * math.sin(3.4 * (t - 3.6)) * sm(14.9, 15.6, t)); prev = a; tgt = a
    for th, deg in PHIT:
        if t >= th:
            tau = t - th; tgt = math.radians(deg)
            a = tgt + (prev - tgt) * math.exp(-2.6 * tau) * math.cos(8.5 * tau); prev = tgt
    return a
PS = .5; PCY = 905; PCX = 456
def pay_scale(fr, t):
    p = {"post": pr(t, EXPR_S + .2, EXPR_S + .55), "base": pr(t, EXPR_S + .5, EXPR_S + .7), "beam": pr(t, EXPR_S + .6, EXPR_S + .9), "strings": pr(t, EXPR_S + .85, EXPR_S + 1.05), "bowl": pr(t, EXPR_S + 1.0, EXPR_S + 1.2)}
    a = pay_angle(t); items, l, r = scale_items(PCX, PCY, PS, a, p)
    org = (PCX - 300, PCY - 80); lay = stroke_items((600, 400), items, org=org)
    fr.alpha_composite(lay, org)
    rent_t = [w for w in W2 if w["t"] == "rent."][0]["s"]
    for e, t0, side in ((l, EXPR_S + 1.1, "L"), (r, EXPR_S + 1.3, "R")):
        sp, sc = (TAG_SPACE, .55) if side == "L" else ((PIN, .5) if t < rent_t else (TAG_RENT, .55))
        t0 = t0 if (side == "L" or t < rent_t) else rent_t
        k = pr(t, t0, t0 + .3)
        if k > 0: place(fr, sp, e[0], e[1] + HANG * PS - 8 - (sp.height * sc) / 2 + 22 + (1 - k) ** 2 * -170, -math.degrees(a) * .3, sc)
def scene_payoff(fr, t, env):
    # expression: one row of big paper-cut tiles, dropped letter by letter from expr_start
    tot = sum(w_ for _, w_ in TILES_BIG) * .68 + 8 * 8; x = -tot / 2
    for i, (sp, w_) in enumerate(TILES_BIG):
        u = x + w_ * .68 / 2; x += w_ * .68 + 8
        tau = t - (EXPR_S + .03 * i)
        if tau < 0: continue
        k = back(pr(tau, 0, .12)); k = max(.05, k)
        wob = 1.4 * math.sin(t * 2.4 + i) * sm(EXPR_S + 1.0, EXPR_S + 1.4, t)
        place(fr, sp, 456 + u, 365 + 40 * (1 - pr(tau, 0, .12)), (1 - k) * (16 if i % 2 else -16) + (2 if i % 2 else -2) + wob, .68 * k)
    pay_scale(fr, t)
    # example cards: ex1 -> swap -> ex2 -> exit before save
    CY = 625
    if E1S <= t < E2S + .1:
        k = back(pr(t, E1S, E1S + .38)); ex = pr(t, E2S - .15, E2S + .1)
        cd = draw_words(PC1, E1_TOK, E1_T, F_PE, t, PLH, PCW / 2 + 30, 30 + 25 + PLH / 2, 30, hl_t0=W1[5]["s"])
        place(fr, cd, 456 - 700 * ex * ex, CY - (1 - k) * 600, -1.2 + 2.5 * ex + 2 * (1 - k))
    if E2S <= t < SAVE_S:
        k = back(pr(t, E2S, E2S + .38)); ex = pr(t, E2E + .15, SAVE_S - .05)
        cd = draw_words(PC2, E2_TOK, E2_T, F_PE, t, PLH, PCW / 2 + 30, 30 + 25 + PLH / 2, 30, hl_t0=W2[-1]["s"])
        place(fr, cd, 456, CY + 40 - (1 - k) * 700, 1.2 - 2 * (1 - k), 1 - .35 * ex, 1 - ex)
    # save: pill + bookmark appear only at save_start
    if t >= SAVE_S:
        p = pr(t, SAVE_S, SAVE_S + .7); bx, by = 140, CY
        pts = [(bx + x - 46, by + y - 74) for x, y in BM_PTS]; fillp = pr(t, SAVE_S + .75, SAVE_S + 1.1)
        lay = Image.new("RGBA", (200, 220), (0, 0, 0, 0))
        if fillp > 0:
            d = ImageDraw.Draw(lay); d.polygon([(x - (bx - 100), y - (by - 110)) for x, y in pts], fill=YEL + (int(255 * fillp),))
        lay.alpha_composite(stroke_items((200, 220), [(pts, p, 12, OFF)], org=(bx - 100, by - 110))); fr.alpha_composite(lay, (bx - 100, by - 110))
        kt = back(pr(t, SAVE_S, SAVE_S + .4))
        place(fr, TAB, 540 + (1 - kt) * 500, CY + 6 * math.sin(t * 2.6), -2.5 + 1.2 * math.sin(t * 2), 1)

# ------------------------------------------------------------------ frame
def render(t):
    fr = Image.new("RGBA", (W, H)); bg(fr, t); scraps(fr, t)
    e = ENV[min(len(ENV) - 1, int(t * FPS))] if t < AUD else 0.0
    place(fr, PILL, 62 + PILL.width / 2 - 14, 262, -1.5)
    if t < 2.92: scene_hook(fr, t, e)
    elif t < 6.8:
        scene_term(fr, t, e)
        if t < 3.3: scene_hook(fr, t, e)
    elif t < 10.0: scene_meaning(fr, t, e)
    elif t < 12.4: scene_en(fr, t, e)
    elif t < 14.72: scene_en(fr, t, e, ko=True)
    else: scene_payoff(fr, t, e)
    bird_on_roof(fr, t, e)
    place(fr, HANDLE_SP, 540, 1588)
    return fr.convert("RGB")

def contrast_report():
    f = lambda c: tuple(c)
    return {"spruce on off-white (hook/example/tiles)": contrast(SP, OFF), "spruce on yellow (tab/tags/ko card)": contrast(SP, YEL),
            "ghost word on off-white (dim, large 132px)": contrast(GHOST, OFF), "ko ghost (62,100,64) on yellow": contrast((62, 100, 64), YEL),
            "off-white on spruce bg (strokes/handle area)": contrast(OFF, SP), "yellow on spruce bg ('?' / slot)": contrast(YEL, SP),
            "spruce on off-white handle": contrast(SP, OFF), "off-white on near-black roof (9,36,14)": contrast(OFF, (9, 36, 14))}

if __name__ == "__main__":
    if "--stills" in sys.argv:
        for ts in sys.argv[sys.argv.index("--stills") + 1].split(","):
            render(float(ts)).save(f"{FR}/kw_{ID}_t{float(ts):05.2f}.png")
        for k, v in contrast_report().items(): print(f"contrast {k}: {v:.2f}")
        sys.exit()
    ad = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
    total = ad + TAIL; N = int(math.ceil(total * FPS)); outp = f"{OUT}/kw_{ID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", MP3, "-filter_complex", f"[1:a]apad=pad_dur={TAIL + 0.5}[a]", "-map", "0:v", "-map", "[a]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-threads", "1", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", outp]
    pr_ = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(N): pr_.stdin.write(render(i / FPS).tobytes())
    pr_.stdin.close(); pr_.wait()
    for k, v in contrast_report().items(): print(f"contrast {k}: {v:.2f}")
    print("wrote", outp, "frames", N)
