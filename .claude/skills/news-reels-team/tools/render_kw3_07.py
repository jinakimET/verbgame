#!/usr/bin/env python3
"""kw3_07 'leverage' - HOLOGRAPHIC + LIQUID MOTION + TEXT SCRAMBLE.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-23-cnn python3 render_kw3_07.py [--stills t1,t2,...]
Needs numpy, Pillow, opencv-python-headless, ffmpeg."""
import json, os, subprocess, sys, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-23-cnn")
OUT = f"{ROOT}/06_keyword_reels/v3"; FR = f"{OUT}/frames"
os.makedirs(FR, exist_ok=True)
ID = "07"; W, H, FPS = 1080, 1920, 30; TAIL = 0.7
MP3 = f"{ROOT}/audio/v3/kw3_{ID}.mp3"
WK = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[ID]
SC = [r for r in json.load(open(f"{ROOT}/03_script/keyword_scripts_v3.json"))["reels"] if r["id"] == ID][0]
words = WK["words"]; beats = WK["beats"]
BS = {b["role"]: b for b in beats}
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc"
def font(w, s): return ImageFont.truetype(CJK % w, s, index=1)
DEEP = np.array([46, 34, 96], np.float32); GRAPE = np.array([74, 56, 142], np.float32)
LAV = (205, 198, 228); MANGO = (255, 191, 72); WHITE = (255, 255, 255); DEEPC = (46, 34, 96)
CX = 456  # centre of safe zone (62..850)

# ---------------------------------------------------------------- helpers
def smooth(a, b, x): x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)
def back(p):
    c = 1.70158; q = p - 1; return 1 + (c + 1) * q ** 3 + c * q ** 2
def lum(c):
    c = np.array(c, np.float64) / 255; c = np.where(c <= .03928, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    return float(.2126 * c[0] + .7152 * c[1] + .0722 * c[2])
def contrast(a, b):
    la, lb = lum(a), lum(b); return (max(la, lb) + .05) / (min(la, lb) + .05)

def hsv_pastel(h, s, v=1.0):
    out = []
    for n in (5, 3, 1):
        k = (n + h * 6) % 6
        out.append(v - v * s * np.clip(np.minimum(np.minimum(k, 4 - k), 1), 0, 1))
    return np.stack(out, -1)

_grid = {}
def grid(w, h):
    if (w, h) not in _grid:
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32); _grid[(w, h)] = (xs, ys)
    return _grid[(w, h)]
def foil(w, h, t, sat=.42, phase=0., glint=True, speed=1.0):
    """holographic foil RGB float (0..255) with hue drifting over time + moving specular glint"""
    xs, ys = grid(w, h)
    hue = (xs * 0.0011 + ys * 0.0009 + 0.12 * np.sin(xs * 0.006 + t * 1.3) - t * 0.16 * speed + phase) % 1.0
    rgb = hsv_pastel(hue, sat) * 255
    if glint:
        span = w + h + 500; pos = ((t * 420 * speed + phase * 900) % span) - 250
        g = np.exp(-(((xs * 0.8 + ys * 0.6) - pos) / 46.0) ** 2)[..., None]
        rgb = rgb + (255 - rgb) * g * 0.85
    return rgb.astype(np.float32)

# worst-case foil luminance (sat .42 text on dark, sat .35 as fill under deep text)
_hh = np.linspace(0, 1, 360)
FOIL_TXT_MINL = min(lum(hsv_pastel(h, .42) * 255) for h in _hh)
FOIL_FILL_MINL = min(lum(hsv_pastel(h, .35) * 255) for h in _hh)

# ---------------------------------------------------------------- background (liquid + holographic)
BW, BH = 270, 480
bxs, bys = np.meshgrid(np.linspace(0, 1, BW, dtype=np.float32) * (BW / BH), np.linspace(0, 1, BH, dtype=np.float32))
BLOB = [(0.0, 0.0, 0.31, 0.7, 0.9, 1.1, 0.16), (1.3, 2.0, 0.52, 0.5, 1.3, 0.8, 0.14), (2.6, 0.7, 0.28, 0.9, 0.7, 1.4, 0.12),
        (3.9, 3.1, 0.62, 0.6, 1.1, 0.9, 0.15), (5.1, 1.2, 0.4, 0.8, 1.5, 0.6, 0.11)]
VIG = (0.55 + 0.45 * smooth(0.05, 0.35, bys) * (1 - smooth(0.78, 1.0, bys) * 0.45))[..., None].astype(np.float32)
def background(t, ripple=None):
    u = bxs + 0.16 * np.sin(5.0 * bys + 0.7 * t) + 0.07 * np.sin(11 * bxs - 1.1 * t)
    v = bys + 0.16 * np.sin(4.2 * bxs - 0.6 * t + 1.0) + 0.07 * np.sin(9 * bys + 0.9 * t)
    f = 0.5 + 0.25 * np.sin(6.5 * u + 3 * v + 0.5 * t) + 0.25 * np.sin(5.0 * v - 4.0 * u - 0.4 * t + 2.0)
    f = f + 0.12 * np.sin(14 * (u + v) + 0.8 * t)
    f = np.clip(f, 0, 1)
    base = DEEP * 0.7 + (GRAPE * 0.95 - DEEP * 0.7) * f[..., None]
    # metaballs
    m = np.zeros_like(f)
    for ph, ph2, ax, ay, sx, sy, r in BLOB:
        cx = (BW / BH) * (0.5 + 0.38 * np.sin(0.35 * t * sx + ph)) ; cy = 0.5 + 0.42 * np.sin(0.3 * t * sy + ph2)
        m += r * r / ((bxs - cx) ** 2 + (bys - cy) ** 2 + 1e-4)
    inside = smooth(0.9, 1.2, m)[..., None]; rim = np.exp(-((m - 1.0) / 0.14) ** 2)[..., None]
    # iridescent hue
    hue = (f * 0.7 + bys * 0.35 + bxs * 0.2 - 0.05 * t) % 1.0
    irid = hsv_pastel(hue, 0.65, 0.9) * 255
    wt = (0.10 + 0.55 * np.exp(-((f - 0.5) / 0.18) ** 2))[..., None] * 0.55
    col = base * (1 - wt) + irid * 0.55 * wt * 1.0
    col = col * (1 - 0.25 * inside) + (GRAPE * 1.15) * 0.25 * inside
    # specular sheen from field gradient
    gy, gx = np.gradient(f)
    spec = np.clip(-(gx * 0.7 + gy * 0.7) * 40, 0, 1) ** 3
    col = col + spec[..., None] * np.array([220, 205, 255], np.float32) * 0.28
    col = col + rim * irid * 0.45
    if ripple is not None:  # (cx, cy, age)
        rcx, rcy, age = ripple
        d = np.sqrt((bxs - rcx * BW / BH) ** 2 + (bys - rcy) ** 2)
        ring = np.exp(-((d - age * 2.4) / 0.07) ** 2) * np.exp(-age * 4.5)
        col = col + ring[..., None] * irid * 0.75
    col = col * VIG
    img = cv2.resize(np.clip(col, 0, 255).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    return np.clip(img, 0, 255)

STARS = np.random.default_rng(7).uniform(0, 1, (22, 4))
def draw_stars(frame, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for sx, sy, ph, sz in STARS:
        a = max(0, math.sin(t * (1.5 + sz * 2) + ph * 9)) ** 3
        if a < 0.05: continue
        x, y = sx * W, (sy * 1750 + 60 + 40 * math.sin(t * .6 + ph * 5)); r = 10 + 24 * sz * a
        pts = [(x, y - r), (x + r * .18, y - r * .18), (x + r, y), (x + r * .18, y + r * .18), (x, y + r), (x - r * .18, y + r * .18), (x - r, y), (x - r * .18, y - r * .18)]
        d.polygon(pts, fill=(255, 245, 255, int(210 * a)))
    blit(frame, np.asarray(ov).astype(np.float32) * np.array([1, 1, 1, 1 / 255], np.float32) * np.array([1, 1, 1, 1], np.float32), 0, 0, straight=True)

# ---------------------------------------------------------------- layers
def blit(frame, layer, x, y, straight=False, alpha=1.0):
    """layer: float32 HxWx4 (premultiplied unless straight, straight alpha 0..1 in ch 3 / rgb 0..255)"""
    h, w = layer.shape[:2]; x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    L = layer[y0 - y:y1 - y, x0 - x:x1 - x]
    a = L[..., 3:4]; rgb = L[..., :3] * a if straight else L[..., :3]
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - a * alpha) + rgb * alpha
def pil_premult(im):
    a = np.asarray(im).astype(np.float32); al = a[..., 3:4] / 255; return np.concatenate([a[..., :3] * al, al], -1)
def warp(layer, s=1.0, dxf=None, dyf=None, cx=None, cy=None):
    h, w = layer.shape[:2]; xs, ys = grid(w, h)
    cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    sx = cx + (xs - cx) / s; sy = cy + (ys - cy) / s
    if dxf is not None: sx = sx + dxf(xs, ys)
    if dyf is not None: sy = sy - dyf(xs, ys)
    return cv2.remap(layer, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
def shadow(layer, dy=7, blur=9, a=0.6):
    al = (layer[..., 3] * 255).astype(np.uint8)
    im = Image.fromarray(al).filter(ImageFilter.GaussianBlur(blur))
    sh = np.asarray(im).astype(np.float32) / 255 * a
    sh = np.roll(sh, dy, 0)
    out = layer.copy(); k = (1 - layer[..., 3:4])
    out[..., 3:4] = layer[..., 3:4] + sh[..., None] * k
    out[..., :3] = layer[..., :3] + np.array([12, 8, 40], np.float32) * (sh[..., None] * k)
    return out

_pm = {}
def rr_mask(w, h, r, inset=0):
    k = (w, h, r, inset)
    if k not in _pm:
        im = Image.new("L", (w * 2, h * 2), 0); ImageDraw.Draw(im).rounded_rectangle((inset * 2, inset * 2, w * 2 - 1 - inset * 2, h * 2 - 1 - inset * 2), r * 2 - inset * 2, fill=255)
        _pm[k] = np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255
    return _pm[k]
def panel(w, h, t, r=48, ring=7, phase=0.0):
    """glass panel: deep->grape gradient at 90% opacity + holographic foil edge + thin top gloss"""
    m = rr_mask(w, h, r); inner = rr_mask(w, h, r, ring); edge = np.clip(m - inner, 0, 1)
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    top = np.array([62, 46, 120], np.float32); bot = DEEP
    body = top * (1 - ys) + bot * ys; body = np.broadcast_to(body, (h, w, 3))
    gl = (np.exp(-((np.linspace(0, 1, h) - 0.03) / 0.02) ** 2) * 0.10).astype(np.float32)[:, None, None]
    body = body + gl * 255
    fo = foil(w, h, t, sat=.55, phase=phase)
    a = (inner * 0.90 + edge * 1.0)[..., None]
    pre = body * (inner * 0.90)[..., None] + fo * edge[..., None]
    out = np.concatenate([pre, a], -1)
    return out.astype(np.float32)

def text_layer(w, h, items, shadow_on=True):
    """items: list of (text, font, (x,y) centre, rgb) -> premult float layer"""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for txt, f, (x, y), col in items: d.text((x, y), txt, font=f, fill=tuple(col) + (255,), anchor="mm")
    L = pil_premult(im); return shadow(L, 6, 6, .5) if shadow_on else L

def wobble_fn(t, amp, ph=0.0, k=0.022, sp=4.2):
    return lambda xs, ys: amp * np.sin(ys * k + t * sp + ph)

def pop(t, t0, dur=0.38, s0=0.55):
    p = np.clip((t - t0) / dur, 0, 1); return s0 + (1 - s0) * back(p) if p < 1 else 1.0
def pop_alpha(t, t0, dur=0.12): return float(np.clip((t - t0) / dur, 0, 1))

# ---------------------------------------------------------------- bird on liquid blob
def bird_scene(frame, t, env, cx, bottom, scale=1.0):
    bw, bh = 820, 420
    # liquid blob + soft glow
    ang = np.linspace(0, 2 * math.pi, 90)
    r = 1 + 0.07 * np.sin(3 * ang + t * 2.2) + 0.05 * np.sin(5 * ang - t * 3.1) + 0.03 * np.sin(2 * ang + t * 1.3)
    ew, eh = 210 * scale, 70 * scale
    px = bw / 2 + ew * r * np.cos(ang); py = bh - 100 + eh * r * np.sin(ang)
    msk = Image.new("L", (bw, bh), 0); ImageDraw.Draw(msk).polygon(list(zip(px, py)), fill=255)
    glow = np.asarray(msk.filter(ImageFilter.GaussianBlur(34))).astype(np.float32) / 255
    msk2 = np.asarray(msk.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    fo = foil(bw, bh, t, sat=.5, phase=0.3)
    lay = np.zeros((bh, bw, 4), np.float32)
    ga = glow[..., None] * 0.55
    lay[..., :3] = fo * ga; lay[..., 3:4] = ga                       # glow (premult)
    hl = np.exp(-((np.mgrid[0:bh, 0:bw][0] - (bh - 118)) / 16.0) ** 2) * msk2 * 0.5
    body = (DEEP * 0.5 + fo * 0.55) * msk2[..., None] + hl[..., None] * 255
    a = msk2[..., None] * 0.95
    lay[..., :3] = lay[..., :3] * (1 - a) + body * 1.0 * a / np.maximum(1, 1) ; lay[..., 3:4] = lay[..., 3:4] * (1 - a) + a
    bx, by = int(cx - bw / 2), int(bottom - bh + 100 * scale + 20)
    # blob drawn centred at (cx, bottom+...) ; adjust so blob sits under the feet
    blit(frame, lay, bx, int(bottom - (bh - 100) + 6))
    # bird floats
    bob = 12 * math.sin(t * 2.4) * scale
    sp = bird.sprite(float(env));
    if scale != 1.0: sp = sp.resize((int(sp.width * scale), int(sp.height * scale)), Image.LANCZOS)
    L = pil_premult(sp)
    blit(frame, L, int(cx - sp.width / 2), int(bottom - sp.height - 18 * scale + bob))

# ---------------------------------------------------------------- scene content
F_HOOK = font("Black", 98)
F_TERM_ANS = font("Black", 84)
F_EN = font("Bold", 64); F_EN_S = font("Bold", 54); F_KO = font("Bold", 54)
F_MEAN = font("Black", 128)
F_SMALL = font("Black", 52)
F_HANDLE = font("Bold", 38); F_PILL = font("Bold", 36)

def wlist(role): return [words[i] for i in range(BS[role]["first_word_idx"], BS[role]["first_word_idx"] + BS[role]["n_words"])]
H_W = {w["t"]: w for w in wlist("hook")}
TERM_T0 = wlist("term")[1]["s"]            # 5.68 'leverage.' start
ANS_T0 = wlist("term")[0]["s"]             # 4.8 '답은,'
EX = wlist("example_en"); KO = wlist("example_ko"); ME = wlist("meaning"); PO = wlist("payoff")

HOOK_LINES = [[("공격은", words[0]["s"], words[1]["s"]), ("늘었는데", words[1]["s"], words[3]["s"])],
              [("협상력은", words[3]["s"], words[4]["s"]), ("왜", words[4]["s"], words[5]["s"])],
              [("약해졌을까?", words[5]["s"], words[6]["s"])]]
HOOK_LINES[0][1] = ("늘었는데", words[1]["s"], words[3]["s"])

def line_x(f, parts, gap=30):
    ws = [f.getlength(p) for p in parts]; tot = sum(ws) + gap * (len(parts) - 1); x = -tot / 2; xs = []
    for w_ in ws: xs.append(x + w_ / 2); x += w_ + gap
    return xs, tot

PW_H, PH_H = 788, 700
def draw_hook(frame, t, env):
    ph = panel(PW_H, PH_H, t); y0 = 300
    pp = min(1.0, 0.9 + 0.1 * back(min(1, t / .35)))
    blit(frame, warp(ph, pp, wobble_fn(t, 2.5, 0, .03, 3)), 62, y0)
    # text layer
    LW, LH = PW_H, PH_H; items = []; line_y = [150, 330, 510]
    colour_of = lambda a, b: (MANGO if a <= t < b else (WHITE if t >= b else LAV))
    for li, line in enumerate(HOOK_LINES):
        xs, tot = line_x(F_HOOK, [p[0] for p in line], 34)
        for (wd, a, b), x in zip(line, xs):
            items.append((wd, F_HOOK, (LW / 2 + x, line_y[li] + 30), colour_of(a, b)))
    PAD = 70
    items = [(a, b, (c[0] + PAD, c[1]), d) for a, b, c, d in items]
    tl = text_layer(LW + 2 * PAD, LH, items)
    burst = 22 * math.exp(-t * 9) + 7
    melt_t = np.clip((t - HOOK_LINES[2][0][1]) / 1.3, 0, 1)   # 약해졌을까? droops as it is spoken
    D = 62 * melt_t ** 0.8 + 6 * math.sin(t * 2.5) * melt_t
    def dyf(xs, ys):
        wgt = smooth(line_y[2] - 70, line_y[2] + 10, ys)
        col = 0.55 + 0.45 * np.sin(xs * 0.028 + t * 2.6)
        return D * wgt * col * (0.4 + 0.6 * smooth(line_y[2] - 70, line_y[2] + 100, ys))
    def dxf(xs, ys):
        return burst * np.sin(ys * 0.025 + t * 5.0) + 5 * np.sin(ys * 0.06 - t * 3) * (1 + melt_t)
    s = 1.0 + 0.28 * math.exp(-t * 11)
    blit(frame, warp(tl, s, dxf, dyf), 62 - PAD, y0 + 12)
    return (62, y0, PW_H, PH_H)

ANS_W, ANS_H = 788, 520
def draw_term(frame, t, env):
    y0 = 430; lt = t - ANS_T0
    ph = panel(ANS_W, ANS_H, t, phase=0.4)
    blit(frame, warp(ph, pop(t, ANS_T0, .4, .6), wobble_fn(t, 3, 1, .03, 3)), 62, y0)
    lay = np.zeros((ANS_H, ANS_W, 4), np.float32)
    ans = text_layer(ANS_W, ANS_H, [("답은,", F_TERM_ANS, (ANS_W / 2, 120), LAV)])
    # leverage text with scramble
    wtxt = "leverage"; fs = 190; f = font("Black", fs)
    while f.getlength(wtxt) > 720: fs -= 4; f = font("Black", fs)
    adv = [f.getlength(c) for c in wtxt]; tot = sum(adv); x = ANS_W / 2 - tot / 2
    rng = np.random.default_rng(int(t * FPS) // 2 * 7 + 3)
    glyphs = "!<>-_/[]{}=+*^?#:;|~"
    fg = font("Black", int(fs * .8))
    mask = Image.new("L", (ANS_W, ANS_H), 0); md = ImageDraw.Draw(mask); fin = True
    for i, c in enumerate(wtxt):
        res = TERM_T0 + 0.14 + i * 0.062
        if t >= res: ch = c
        elif t >= TERM_T0: ch = glyphs[rng.integers(len(glyphs))]; fin = False
        else: ch = "?"; fin = False
        md.text((x + adv[i] / 2, 330), ch, font=(f if t >= res else fg), fill=255 if (t >= TERM_T0) else int(80 + 50 * math.sin(t * 9)), anchor="mm"); x += adv[i]
    m = np.asarray(mask).astype(np.float32) / 255
    fo = foil(ANS_W, ANS_H, t, sat=.42, speed=1.6)
    tlayer = np.concatenate([fo * m[..., None], m[..., None]], -1)
    # unresolved glyph flicker tinted mango
    tlayer = shadow(tlayer, 8, 8, .55)
    jit = 0 if fin else 5
    ans_a = ans
    wob = wobble_fn(t, 6 + 10 * math.exp(-max(0, t - TERM_T0) * 4), 0, .02, 6)
    blit(frame, warp(ans_a, pop(t, ANS_T0 + .05, .3, .6), cx=ANS_W / 2, cy=120), 62, y0)
    blit(frame, warp(tlayer, 1 + 0.16 * math.exp(-max(0, t - TERM_T0) * 10) * (t >= TERM_T0), wob), 62, y0)
    return (62, y0, ANS_W, ANS_H)

def draw_meaning(frame, t, env):
    out = []
    rows = [("영향력", ME[0]["s"], 380, 62, 700), ("협상력", ME[1]["s"], 760, 150, 700)]
    # small foil tag
    for i, (txt, t0, y0, x0, w) in enumerate(rows):
        h = 290
        ghost = t < t0
        ph = panel(w, h, t, r=60, phase=i * .37)
        s = 1.0 if ghost else pop(t, t0, .42, .5)
        blit(frame, warp(ph, s, wobble_fn(t, 3, i, .03, 3)), x0, y0)
        fo = foil(w, h, t, sat=.42, speed=1.4, phase=i * .3)
        gk = (0.3 + 0.1 * math.sin(t * 8)) if ghost else 1.0
        im = Image.new("L", (w, h), 0); ImageDraw.Draw(im).text((w / 2, h / 2 + 6), txt, font=F_MEAN, fill=255, anchor="mm")
        m = np.asarray(im).astype(np.float32) / 255 * gk
        tl = shadow(np.concatenate([fo * m[..., None], m[..., None]], -1), 7, 7, .55)
        dec = 0 if ghost else math.exp(-(t - t0) * 5)
        blit(frame, warp(tl, s, wobble_fn(t, 4 + 18 * dec, i, .024, 5)), x0, y0)
        out.append((x0, y0, w, h))
    # small dot between
    return out

def lay_en(f, tokens, hl_idx, maxw, pad=18):
    """tokens (text); returns lines of list of (idx,x_left,width)"""
    sp = f.getlength(" ") + 6; lines = [[]]; cur = 0
    for i, tk in enumerate(tokens):
        w = f.getlength(tk) + (2 * pad if i == hl_idx else 0)
        if lines[-1] and cur + sp + w > maxw: lines.append([]); cur = 0
        x = cur + (sp if lines[-1] else 0); lines[-1].append((i, x, w)); cur = x + w
    return lines

EN_TOK = ["Low", "sales", "weakened", "our", "leverage", "in", "talks."]; HL = 4
def draw_en_text(frame, t, ox, oy, f, maxw, lh, t_off=0.0, colour=WHITE, all_on=False, tag_t=None):
    """draw example sentence with 'leverage' foil box; returns bbox"""
    lines = lay_en(f, EN_TOK, HL, maxw)
    wmax = max(l[-1][1] + l[-1][2] for l in lines); H_ = lh * len(lines)
    im = Image.new("RGBA", (int(maxw) + 80, H_ + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    boxes = []
    for li, line in enumerate(lines):
        lw = line[-1][1] + line[-1][2]; x0 = (maxw - lw) / 2 + 40
        for i, x, w in line:
            tk = EN_TOK[i]; s_t = EX[i]["s"]
            cy = 30 + li * lh + lh / 2
            if i == HL:
                boxes.append((x0 + x, cy, w)); continue
            active = (s_t <= t < s_t + .32) and not all_on
            col = (MANGO if active else colour) if (all_on or t >= s_t) else (150, 140, 190)
            d.text((x0 + x + w / 2, cy), tk, font=f, fill=col + (255,), anchor="mm")
    L = shadow(pil_premult(im), 5, 5, .5)
    # foil box for leverage
    for bx, cy, w in boxes:
        s_t = EX[HL]["s"]; bw_, bh_ = int(w), int(lh * 0.86)
        p = pop(t, s_t, .35, .5) if (not all_on and t >= s_t) else 1.0
        bl = np.zeros((bh_ + 60, bw_ + 60, 4), np.float32)
        mm = rr_mask(bw_, bh_, int(bh_ * .32))
        fo = foil(bw_, bh_, t, sat=.35, speed=1.8, phase=.2)
        bl[30:30 + bh_, 30:30 + bw_, :3] = fo * mm[..., None]; bl[30:30 + bh_, 30:30 + bw_, 3] = mm
        bl = shadow(bl, 5, 6, .5)
        # text
        im2 = Image.new("RGBA", bl.shape[1::-1], (0, 0, 0, 0)); ImageDraw.Draw(im2).text((bl.shape[1] / 2, bl.shape[0] / 2 + 2), "leverage", font=f, fill=DEEPC + (255,), anchor="mm")
        t2 = pil_premult(im2); bl = bl * (1 - t2[..., 3:4]) + t2
        bl = warp(bl, p, wobble_fn(t, 2, 0, .03, 4))
        # compose into L at box position
        blit_into(L, bl, int(bx - 30 + 0), int(cy - bl.shape[0] / 2))
    blit(frame, L, ox - 40, oy - 30)
    return (ox, oy, int(maxw), H_)
def blit_into(L, layer, x, y):
    h, w = layer.shape[:2]; H_, W_ = L.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W_, x + w), min(H_, y + h)
    if x1 <= x0 or y1 <= y0: return
    s = layer[y0 - y:y1 - y, x0 - x:x1 - x]; L[y0:y1, x0:x1] = L[y0:y1, x0:x1] * (1 - s[..., 3:4]) + s

def draw_example_en(frame, t, env):
    pw, ph_ = 788, 480; y0 = 520
    p = panel(pw, ph_, t, phase=.7); s = pop(t, BS["example_en"]["start"], .35, .75)
    blit(frame, warp(p, s, wobble_fn(t, 3, 2, .03, 3)), 62, y0)
    # tag
    draw_en_text(frame, t, 62 + 24, y0 + 120, F_EN, pw - 48, 118)
    return (62, y0, pw, ph_)

def draw_example_ko(frame, t, env):
    pw = 788; y0 = 300; h1 = 330
    p = panel(pw, h1, t, phase=.7); blit(frame, warp(p, 1, wobble_fn(t, 2.5, 2, .03, 3)), 62, y0)
    draw_en_text(frame, t, 62 + 24, y0 + 70, F_EN_S, pw - 48, 104, all_on=True)
    y1 = 700; h2 = 400
    s = pop(t, BS["example_ko"]["start"], .4, .6)
    p2 = panel(pw, h2, t, phase=.1, r=70); blit(frame, warp(p2, s, wobble_fn(t, 3, 1, .03, 3)), 62, y1)
    KT = ["낮은", "매출이", "협상에서", "우리의", "힘을", "약하게", "했어요."]; lines = [[0, 1, 2], [3, 4, 5, 6]]
    im = Image.new("RGBA", (pw, h2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for li, ln in enumerate(lines):
        sp = F_KO.getlength(" ") + 8; ws = [F_KO.getlength(KT[i]) for i in ln]; tot = sum(ws) + sp * (len(ln) - 1); x = (pw - tot) / 2
        for i, w_ in zip(ln, ws):
            s_t = KO[i]["s"]
            active = s_t <= t < s_t + .3
            col = (MANGO if (active or i == 4) else WHITE) if t >= s_t else (150, 140, 190)
            d.text((x + w_ / 2, 130 + li * 120), KT[i], font=F_KO, fill=col + (255,), anchor="mm")
            x += w_ + sp
    L = shadow(pil_premult(im), 5, 5, .5)
    # droop on '힘을 약하게'
    ts = KO[5]["s"]; dm = np.clip((t - ts) / 0.8, 0, 1)
    def dyf(xs, ys): return 10 * dm * (0.5 + 0.5 * np.sin(xs * .03 + t * 2)) * smooth(160, 210, ys)
    blit(frame, warp(L, 1, wobble_fn(t, 3, 0, .03, 3), dyf), 62, y1)
    return (62, y0, pw, h1)

def draw_payoff(frame, t, env):
    t0 = BS["payoff"]["start"]; lt = t - t0
    pw, ph_ = 760, 200; y0 = 800; s = pop(t, t0, .45, .45) * (1 + 0.025 * math.sin(t * 6))
    m = rr_mask(pw, ph_, 100); inner = rr_mask(pw, ph_, 100, 8); edge = np.clip(m - inner, 0, 1)
    fo = foil(pw, ph_, t, sat=.35, speed=2.4, phase=.5); fo2 = foil(pw, ph_, t, sat=.7, speed=2.4, phase=.5, glint=False) * .85
    rgb = fo * inner[..., None] + fo2 * edge[..., None]
    a = m[..., None]; lay = np.concatenate([rgb * a, a], -1)
    # bookmark icon + text
    im = Image.new("RGBA", (pw, ph_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ix, iy = 130, ph_ / 2
    d.polygon([(ix - 34, iy - 52), (ix + 34, iy - 52), (ix + 34, iy + 52), (ix, iy + 24), (ix - 34, iy + 52)], fill=DEEPC + (255,))
    d.text((pw / 2 + 60, ph_ / 2 + 4), "저장해 두기", font=font("Black", 82), fill=DEEPC + (255,), anchor="mm")
    tx = pil_premult(im); lay = lay * (1 - tx[..., 3:4]) + tx
    lay = shadow(lay, 12, 18, .6)
    dec = math.exp(-lt * 4)
    blit(frame, warp(lay, s, wobble_fn(t, 3 + 14 * dec, 0, .03, 5)), 62 + (788 - pw) // 2 - 30, y0)
    # foil tag above
    tg = text_layer(788, 200, [("leverage", font("Black", 96), (394, 100), WHITE)], shadow_on=True)
    fo3 = foil(788, 200, t, sat=.42, speed=1.6)
    im3 = Image.new("L", (788, 200), 0); ImageDraw.Draw(im3).text((394, 100), "leverage", font=font("Black", 112), fill=255, anchor="mm")
    m3 = np.asarray(im3).astype(np.float32) / 255
    # backing glass chip so foil text keeps contrast
    ch = panel(560, 170, t, r=85, ring=5, phase=.3)
    blit(frame, warp(ch, pop(t, t0 + .1, .4, .5)), 62 + 114, 470)
    tl = shadow(np.concatenate([fo3 * m3[..., None], m3[..., None]], -1), 6, 6, .5)
    blit(frame, warp(tl, pop(t, t0 + .1, .4, .5)), 62, 455)
    return (62, y0, pw, ph_)

# ---------------------------------------------------------------- static overlays
def top_pill(frame, t):
    w, h = 470, 64; m = rr_mask(w, h, 32); fo = foil(w, h, t, sat=.33, speed=1.2)
    a = m[..., None]; lay = np.concatenate([fo * a, a], -1)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((w / 2, h / 2 + 1), "NEWS ENGLISH · CNN", font=F_PILL, fill=DEEPC + (255,), anchor="mm")
    tx = pil_premult(im); lay = lay * (1 - tx[..., 3:4]) + tx
    blit(frame, shadow(lay, 4, 6, .4), CX - w // 2, 228)
HANDLE = "지나쌤영어  @jina.ssam_english"
def handle(frame, t):
    w = int(F_HANDLE.getlength(HANDLE)) + 70; h = 66
    lay = panel(w, h, t, r=33, ring=3, phase=.2)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((w / 2, h / 2 + 1), HANDLE, font=F_HANDLE, fill=WHITE + (255,), anchor="mm")
    tx = pil_premult(im); lay = lay * (1 - tx[..., 3:4]) + tx
    blit(frame, lay, 540 - w // 2, 1588 - h // 2)

# ---------------------------------------------------------------- timeline
def beat_of(t):
    cur = beats[0]
    for b in beats:
        if b["start"] <= t + 1e-6: cur = b
    return cur
BIRD = {"hook": (330, 1400, 1.0), "term": (640, 1400, 1.0), "meaning": (650, 1400, 1.0),
        "example_en": (250, 1400, 1.0), "example_ko": (700, 1440, 1.0), "payoff": (456, 1440, 1.25)}
RIP = {"hook": (0.5, 0.35), "term": (0.5, 0.45), "meaning": (0.3, 0.55), "example_en": (0.7, 0.4), "example_ko": (0.4, 0.6), "payoff": (0.5, 0.5)}
DUR = max(b["end"] for b in beats)
ENV = bird.envelope(MP3, FPS)

def render(t):
    b = beat_of(t); role = b["role"]
    rp = RIP[role]; age = t - b["start"]
    bg = background(t, (rp[0], rp[1], age) if age < 1.2 and t > 0.05 else None)
    frame = bg.copy(); draw_stars(frame, t)
    top_pill(frame, t)
    env = ENV[min(int(t * FPS), len(ENV) - 1)] if t <= DUR + .3 else 0
    {"hook": draw_hook, "term": draw_term, "meaning": draw_meaning, "example_en": draw_example_en,
     "example_ko": draw_example_ko, "payoff": draw_payoff}[role](frame, t, env)
    bx, by, sc = BIRD[role]
    bird_scene(frame, t, env, bx, by, sc)
    handle(frame, t)
    return np.clip(frame, 0, 255).astype(np.uint8)

def contrast_report():
    # worst case: panel body = top colour at 90% over a pure-white background + 10% gloss
    worst = 0.9 * np.array([62, 46, 120]) + 0.1 * 255; worst = np.clip(worst + 25, 0, 255)
    rows = {"white on panel": contrast(WHITE, worst), "lavender on panel": contrast(LAV, worst), "mango on panel": contrast(MANGO, worst),
            "foil text(min L) on panel": (lum(worst) + .05) and (( FOIL_TXT_MINL + .05) / (lum(worst) + .05)),
            "deep on foil fill (min L)": (FOIL_FILL_MINL + .05) / (lum(DEEPC) + .05),
            "deep on mango": contrast(DEEPC, MANGO)}
    return rows

if __name__ == "__main__":
    total = DUR + TAIL; N = int(math.ceil(total * FPS))
    if "--stills" in sys.argv:
        for ts in sys.argv[sys.argv.index("--stills") + 1].split(","):
            Image.fromarray(render(float(ts))).save(f"{FR}/kw3_{ID}_t{float(ts):05.2f}.png")
        sys.exit()
    audio_d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
    total = audio_d + TAIL; N = int(math.ceil(total * FPS))
    outp = f"{OUT}/kw3_{ID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", MP3, "-filter_complex", f"[1:a]apad=pad_dur={TAIL + 0.5}[a]", "-map", "0:v", "-map", "[a]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-threads", "1", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", outp]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(N):
        pr.stdin.write(render(i / FPS).tobytes())
    pr.stdin.close(); pr.wait()
    for k, v in contrast_report().items(): print(f"contrast {k}: {v:.2f}")
    print("wrote", outp, "frames", N)
