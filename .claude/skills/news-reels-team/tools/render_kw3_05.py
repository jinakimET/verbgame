#!/usr/bin/env python3
"""kw3_05  'at the highest level since'  -- HALFTONE + INFINITE ZOOM + ISOMETRIC (card-2 palette).
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-23-cnn python3 render_kw3_05.py [--test t1 t2 ...]
Everything is numpy-vectorised (halftone cell tables cached, tunnel in rounded-rect log space) + PIL for text/iso polygons."""
import json, os, subprocess, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird as BIRD

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-23-cnn")
RID = "05"; W, H, FPS = 1080, 1920, 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels/v3"; FR = f"{OUT}/frames"
FB = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", 1)
FBD = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 1)
SX0, SX1 = 62, 850; SCX = (SX0 + SX1) // 2

def hx(s): return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
GRAPE, LAV, MANGO, DEEP = hx("#4A388E"), hx("#CDC6E4"), hx("#FFBF48"), hx("#2E2260")
WHITE = (255, 255, 255); RED = (255, 69, 58)
def mix(a, b, t): return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))
def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + 0.05) / (lb + 0.05)
_fc = {}
def font(spec, size):
    k = (spec, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(spec[0], size, index=spec[1])
    return _fc[k]
def tsize(f, t):
    b = f.getbbox(t); return b[2] - b[0], b[3] - b[1]
def ease(p): p = min(1, max(0, p)); return p * p * (3 - 2 * p)
def eout(p): p = min(1, max(0, p)); return 1 - (1 - p) ** 3
def eback(p):
    p = min(1, max(0, p)); c = 1.70158; q = p - 1; return 1 + (c + 1) * q ** 3 + c * q ** 2

# ------------------------------------------------------------------ input
SC = [r for r in json.load(open(f"{ROOT}/03_script/keyword_scripts_v3.json"))["reels"].values()
      if r["id"] == RID][0] if isinstance(json.load(open(f"{ROOT}/03_script/keyword_scripts_v3.json"))["reels"], dict) else \
     [r for r in json.load(open(f"{ROOT}/03_script/keyword_scripts_v3.json"))["reels"] if r["id"] == RID][0]
WK = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[RID]
MP3 = f"{ROOT}/audio/v3/kw3_{RID}.mp3"
words = WK["words"]; BT = {b["role"]: b["start"] for b in WK["beats"]}
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3],
                           capture_output=True, text=True).stdout)
TOTAL = round((dur + TAIL) * FPS) / FPS
NF = int(round(TOTAL * FPS))
def ws(i): return words[i]["s"]
T_HOOK, T_TERM, T_MEAN, T_EN, T_KO, T_PAY = [BT[k] for k in ("hook", "term", "meaning", "example_en", "example_ko", "payoff")]
T_AT, T_HIGHEST, T_LEVEL, T_SINCE = ws(13), ws(15), ws(16), ws(17)
BOUNDS = [0, T_TERM, T_MEAN, T_EN, T_KO, T_PAY, 1e9]

# ------------------------------------------------------------------ halftone engine (cell tables cached)
class HT:
    """dot screen over region (x0,y0,w,h) with pitch p and angle; radius table is per CELL so per-frame work is a gather."""
    def __init__(self, x0, y0, w, h, pitch, angle):
        self.x0, self.y0, self.w, self.h, self.p = x0, y0, w, h, pitch
        th = math.radians(angle); c, s = math.cos(th), math.sin(th)
        yy, xx = np.mgrid[y0:y0 + h, x0:x0 + w].astype(np.float32)
        u = (xx * c + yy * s) / pitch; v = (-xx * s + yy * c) / pitch
        iu = np.floor(u).astype(np.int32); iv = np.floor(v).astype(np.int32)
        umin, vmin = iu.min(), iv.min(); nv = iv.max() - vmin + 1; nu = iu.max() - umin + 1
        self.cid = ((iu - umin) * nv + (iv - vmin)).astype(np.int32)
        self.d = (np.hypot(u - iu - .5, v - iv - .5) * pitch).astype(np.float32)
        cu, cv = np.meshgrid(np.arange(nu) + umin + .5, np.arange(nv) + vmin + .5, indexing="ij")
        self.cx = ((cu * c - cv * s) * pitch).ravel().astype(np.float32)   # global coords of cell centres
        self.cy = ((cu * s + cv * c) * pitch).ravel().astype(np.float32)
    def alpha(self, rad):
        """rad: per-cell radius in px (len = ncells)"""
        return np.clip(rad[self.cid] - self.d + 0.5, 0, 1)
    def sample(self, img, ox=0, oy=0):
        """sample a 2D field image (placed at ox,oy) at cell centres; outside = 0"""
        xi = np.round(self.cx - ox).astype(np.int32); yi = np.round(self.cy - oy).astype(np.int32)
        ok = (xi >= 0) & (yi >= 0) & (xi < img.shape[1]) & (yi < img.shape[0])
        out = np.zeros(len(xi), np.float32); out[ok] = img[yi[ok], xi[ok]]; return out

def comp(canvas, color, a, x0=0, y0=0):
    """canvas uint8 HxWx3 ; color (3,) or array HxWx3 ; a HxW float 0..1"""
    h, w = a.shape; reg = canvas[y0:y0 + h, x0:x0 + w].astype(np.float32)
    col = np.asarray(color, np.float32)
    reg += (col - reg) * a[..., None]; canvas[y0:y0 + h, x0:x0 + w] = reg.astype(np.uint8)

# ------------------------------------------------------------------ text helpers
def txt_layer(text, f, fill, pad=0):
    w, h = tsize(f, text); bb = f.getbbox(text)
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=f, fill=fill + (255,)); return im
def fit_font(spec, text, maxw, hi, lo=40):
    for s in range(hi, lo, -2):
        if tsize(font(spec, s), text)[0] <= maxw: return font(spec, s)
    return font(spec, lo)
def paste(canvas, im, x, y, alpha=1.0, scale=1.0):
    """alpha-composite PIL RGBA onto uint8 canvas (clipped)"""
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    a = np.asarray(im)
    x, y = int(x), int(y); h, w = a.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0: return
    sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
    al = (sub[..., 3:4].astype(np.float32) / 255) * alpha
    reg = canvas[y0:y1, x0:x1].astype(np.float32)
    canvas[y0:y1, x0:x1] = (reg + (sub[..., :3].astype(np.float32) - reg) * al).astype(np.uint8)

# ------------------------------------------------------------------ isometric primitives (drawn 2x supersampled in a local layer)
C30, S30 = math.cos(math.radians(30)), 0.5
def iso_pt(x, y, z, ox, oy): return (ox + (x - y) * C30, oy + (x + y) * S30 - z)   # x -> down-right, y -> down-left
def iso_pt2(x, y, z, ox, oy): return (ox + (x + y) * C30, oy + (y - x) * S30 - z)   # x -> up-right, y -> down-right
def off(ox, oy, x, y): return ox + (x - y) * C30, oy + (x + y) * S30
class IsoLayer:
    def __init__(self, w, h, ss=2):
        self.w, self.h, self.ss = w, h, ss
        self.im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
    def poly(self, pts, col, outline=None):
        self.d.polygon([(x * self.ss, y * self.ss) for x, y in pts], fill=col + (255,))
        if outline: self.d.line([(x * self.ss, y * self.ss) for x, y in pts + [pts[0]]], fill=outline + (255,), width=self.ss * 2)
    def box(self, ox, oy, lx, ly, hh, z0, cols, proj=iso_pt):
        """box of footprint lx*ly, height hh on z0. cols=(top,left,right). origin (ox,oy) = ground corner."""
        P = lambda x, y, z: proj(x, y, z + z0, ox, oy)
        a, b, c, d = P(0, 0, hh), P(lx, 0, hh), P(lx, ly, hh), P(0, ly, hh)
        e, f_, g = P(0, ly, 0), P(lx, ly, 0), P(lx, 0, 0)
        # proj2: x up-right, y down-right.  visible: top, front-left (y=ly face), front-right (x=lx? -> faces down-right)
        self.poly([d, c, f_, e], cols[1])        # y=ly face (faces down-left in view)
        self.poly([b, c, f_, g], cols[2])        # x=lx face (faces down-right)
        self.poly([a, b, c, d], cols[0])         # top
    def out(self): return self.im.resize((self.w, self.h), Image.LANCZOS)
def shades(c): return (mix(c, WHITE, .28), c, mix(c, (0, 0, 0), .30))   # top, left, right

# ------------------------------------------------------------------ background (halftone drift) + tunnel
BG_HT = HT(0, 0, W, H, 44, 22)
def bg_halftone(canvas, t, base, dot, strength=1.0, wave=1.0):
    f = 0.5 + 0.5 * np.sin(BG_HT.cx / 310 + BG_HT.cy / 520 - t * 0.9 * wave)
    rad = (f * 0.58 * 44 * strength).astype(np.float32)
    canvas[:] = base; comp(canvas, dot, BG_HT.alpha(rad))

# tunnel geometry at half-res (static), centre = (SCX, 860)
TH, TW = H // 2, W // 2; TCX, TCY = SCX / 2, 860 / 2
_yy, _xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
_dx, _dy = (_xx - TCX) / 270, (_yy - TCY) / 480
TN = np.maximum((np.abs(_dx) ** 6 + np.abs(_dy) ** 6) ** (1 / 6), 0.004).astype(np.float32)
TLOG = np.log(TN); TTH = ((np.arctan2(_dy, _dx) / (2 * math.pi) + .5) * 40).astype(np.float32)
RR = 1.62; LNR = math.log(RR)
def tunnel(canvas, phase, mode=0):
    L = TLOG / LNR - phase; i = np.floor(L); fr = L - i
    even = (i.astype(np.int32) % 2 == 0)
    base = np.where(even[..., None], np.array(GRAPE, np.float32), np.array(DEEP, np.float32)).astype(np.float32)
    # dot texture inside each ring: radius grows toward the viewer side of the ring
    ang = TTH - np.floor(TTH) - .5; rad = fr - .5
    dist = np.hypot(rad, ang)
    r = 0.12 + 0.34 * fr
    dots = np.clip((r - dist) * 9 + .5, 0, 1) * np.clip(TN * 6, 0, 1)
    dcol = np.where(even[..., None], np.array(mix(GRAPE, LAV, .28), np.float32), np.array(mix(DEEP, GRAPE, .75), np.float32))
    base = base + (dcol - base) * dots[..., None]
    # frame lines (thickness proportional to scale -> grows as it nears the viewer)
    lw = np.clip(0.07 + 0.0 * fr, 0, 1)
    line = np.clip((lw - fr) * TN * 70 + .5, 0, 1)
    lcol = np.where((i.astype(np.int32) % 4 == 0)[..., None], np.array(MANGO, np.float32), np.array(LAV, np.float32))
    base = base + (lcol - base) * line[..., None]
    img = np.clip(base, 0, 255).astype(np.uint8)
    canvas[:] = cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)

def tunnel_phase(t, t0, rev=False):
    tau = max(0.0, t - t0)
    return 0.55 * tau + 2.6 * 0.35 * (1 - math.exp(-tau / 0.35))

# ------------------------------------------------------------------ shared overlays
PILL = None
def pill_layer():
    global PILL
    if PILL is None:
        f = font(FB, 34); tt = "NEWS ENGLISH · CNN"; w, h = tsize(f, tt)
        lay = IsoLayer(w + 130, 62); ss = lay.ss
        lay.d.rounded_rectangle((0, 2 * ss, (w + 130) * ss - 1, 60 * ss), 30 * ss, fill=MANGO + (255,))
        lay.box(14, 40, 18, 18, 18, 0, shades(DEEP))
        im = lay.out(); ImageDraw.Draw(im).text((70, 31 - h // 2 - f.getbbox(tt)[1] + 0), tt, font=f, fill=DEEP + (255,))
        PILL = im
    return PILL
def handle(canvas, fg):
    f = font(FB, 34); t = "지나쌤영어  @jina.ssam_english"; im = txt_layer(t, f, WHITE)
    pw, ph = im.width + 44, 56; pl = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(pl).rounded_rectangle((0, 0, pw - 1, ph - 1), 28, fill=DEEP + (225,)); pl.alpha_composite(im, (22, (ph - im.height) // 2))
    paste(canvas, pl, (W - pw) // 2, 1588 - ph // 2)

# bird on isometric block
def bird_on_block(canvas, mouth, cx, base_y, t, size=240, bob=True, blockcol=MANGO, block=True):
    """bird stands on the top face of an isometric block; base_y = y of the block top-face centre"""
    sp = BIRD.sprite(mouth); s = size / sp.height
    if s != 1: sp = sp.resize((int(sp.width * s), int(sp.height * s)), Image.LANCZOS)
    lay = IsoLayer(260, 190)
    lay.box(130, 50, 100, 100, 34, 0, shades(blockcol))
    paste(canvas, lay.out(), cx - 130, base_y - 66)
    by = base_y + 2 - (abs(math.sin(t * 9)) * 6 if mouth > .3 else 0)
    paste(canvas, sp.convert("RGBA"), cx - sp.width // 2, int(by - sp.height))

# ------------------------------------------------------------------ hook : halftone "3" + isometric tankers
def make_glyph_mask(ch, size, spec=FB):
    f = font(spec, size); bb = f.getbbox(ch); im = Image.new("L", (bb[2] - bb[0] + 60, bb[3] - bb[1] + 60), 0)
    ImageDraw.Draw(im).text((30 - bb[0], 30 - bb[1]), ch, font=f, fill=255)
    return im
G3 = make_glyph_mask("3", 860)                          # gigantic 3
G3 = G3.resize((int(G3.width * 1.0), int(G3.height * 1.0)))
GW, GH = G3.size
G3X, G3Y = 100, 300
G3HT = HT(G3X, G3Y, GW, GH, 20, 45)
_g3 = cv2.GaussianBlur(np.asarray(G3).astype(np.float32) / 255, (0, 0), 9)
_g3col = np.zeros((GH, GW, 3), np.float32)
_gy = np.linspace(0, 1, GH)[:, None]
for k in range(3): _g3col[..., k] = (MANGO[k] * (1 - _gy ** 1.4) + mix(MANGO, LAV, .75)[k] * _gy ** 1.4)
def halftone_glyph(canvas, htab, gblur, gcol, gx, gy, t, pulse, rmax=0.64, fx=0.0):
    p = htab.p
    # field sampled at cell centres: mask * moving gradient wave (shading)
    f = htab.sample(gblur, gx, gy)
    wave = 0.5 + 0.5 * np.sin((htab.cx + htab.cy) / 330 * 2 * math.pi * 0.6 - t * 3.2)
    shade = 0.50 + 0.50 * wave
    f = np.clip((f - 0.12) / 0.7, 0, 1) * shade * (1 + fx)
    rad = (np.clip(f, 0, 1.0) * rmax * p * pulse).astype(np.float32)
    a = htab.alpha(rad)
    comp(canvas, gcol, a, htab.x0, htab.y0)

def draw_tanker(lay, ox, oy, col, k=1.32):
    """isometric tanker running down-right: hull box + 3 deck tanks + cabin box (ox,oy = back corner of hull)"""
    lay.box(ox, oy, 130 * k, 46 * k, 28 * k, 0, shades(col))
    for j in range(3):
        gx, gy = off(ox, oy, (12 + j * 34) * k, 8 * k); lay.box(gx, gy, 26 * k, 30 * k, 18 * k, 28 * k, shades(LAV))
    gx, gy = off(ox, oy, 104 * k, 6 * k); lay.box(gx, gy, 22 * k, 34 * k, 44 * k, 28 * k, shades(MANGO))
def hit_mark(lay, cx, cy, size, rot=0.0):
    pts = []
    for k in range(16):
        r = size if k % 2 == 0 else size * 0.48; a = rot + k * math.pi / 8
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    lay.poly(pts, RED, outline=WHITE)
    lay.poly([(cx + size * .22 * math.cos(k * math.pi / 3), cy + size * .22 * math.sin(k * math.pi / 3)) for k in range(6)], MANGO)

TK_T = [0.14, 0.60, 1.06]                           # tankers appear one by one (counter 1->2->3)
TK_POS = [(110, 20), (310, 55), (510, 90)]          # back-corner (x,y) of each hull in the 700x330 layer
TK_COL = [GRAPE, mix(GRAPE, LAV, .3), GRAPE]
def scene_hook(canvas, t):
    bg_halftone(canvas, t, DEEP, mix(DEEP, GRAPE, .55))
    bump = sum(math.exp(-((t - h) / 0.12) ** 2) for h in TK_T)
    pulse = 1.0 + 0.04 * math.sin(t * 5.0) + 0.10 * bump
    s = 1.0 + 0.05 * bump
    sl = eback(t / 0.30) if t < 0.30 else 1.0
    sc = (1.0 + 0.10 * (1 - sl)) * s
    gb = cv2.GaussianBlur(np.asarray(G3.resize((max(1, int(GW * sc)), max(1, int(GH * sc))), Image.BILINEAR)).astype(np.float32) / 255, (0, 0), 9)
    gh, gw = gb.shape; pad_img = np.zeros((GH, GW), np.float32); oy, ox = (GH - gh) // 2, (GW - gw) // 2
    if oy >= 0 and ox >= 0: pad_img[oy:oy + gh, ox:ox + gw] = gb
    else: pad_img = gb[-oy:-oy + GH, -ox:-ox + GW]
    halftone_glyph(canvas, G3HT, pad_img, _g3col, G3X, G3Y, t, pulse)
    # "척": solid counter word beside the dots (slides in at frame 0, visible from the first frame)
    f = font(FB, 230); ch = txt_layer("\ucc99", f, LAV); pc = eout(t / 0.25)
    paste(canvas, ch, 618 + 40 * (1 - pc), G3Y + GH - 60 - ch.height, alpha=1.0)
    # sub label: whole sentence visible at frame 0 as ghost, each word lights up at its spoken start
    sf = fit_font(FB, "\uc774\ud2c0 \uc0ac\uc774 \uacf5\uaca9\ubc1b\uc740 \uc720\uc870\uc120\uc774\uc5d0\uc694.", 788, 54, 44)
    parts = [("\uc774\ud2c0", 1), ("\uc0ac\uc774", 2), ("\uacf5\uaca9\ubc1b\uc740", 3), ("\uc720\uc870\uc120\uc774\uc5d0\uc694.", 4)]
    spc = int(sf.size * 0.28); x = 62
    for w_, idx in parts:
        p = ease((t - words[idx]["s"]) / 0.15); tl = txt_layer(w_, sf, mix(mix(DEEP, LAV, .42), WHITE, p))
        paste(canvas, tl, x, G3Y + GH + 6 - 5 * p, alpha=1.0, scale=1.0); x += tl.width + spc
    # tankers
    lay = IsoLayer(720, 330)
    for i, (tx, ty) in enumerate(TK_POS):
        p = (t - TK_T[i]) / 0.30
        if p < 0:
            gl = IsoLayer(720, 330); draw_tanker(gl, tx, ty + 70, mix(DEEP, LAV, .35)); gi = gl.out(); gi.putalpha(gi.getchannel("A").point(lambda v: int(v * .28)))
            lay.im.alpha_composite(gi.resize(lay.im.size)); continue
        yoff = (1 - eback(p)) * -140 if p < 1 else 0
        yb = yoff + math.sin(t * 2.2 + i * 1.7) * 5
        draw_tanker(lay, tx, ty + 70 + yb, TK_COL[i])
        hp = (t - TK_T[i] - 0.16) / 0.2
        if hp > 0:
            hs = 38 * eback(hp) if hp < 1 else 38 + 3 * math.sin(t * 9 + i)
            hx_, hy_ = off(tx, ty + 70 + yb, 130 * 1.32, 24 * 1.32)
            hit_mark(lay, hx_ - 4, hy_ - 14, hs, rot=0.25 * i)
            ring = (t - TK_T[i] - 0.16) / 0.5
            if 0 < ring < 1:
                r_ = (24 + 80 * ring) * 2; lay.d.ellipse([(hx_ - 4) * 2 - r_, (hy_ - 14) * 2 - r_, (hx_ - 4) * 2 + r_, (hy_ - 14) * 2 + r_],
                                                        outline=RED + (int(255 * (1 - ring)),), width=7)
    paste(canvas, lay.out(), 150, G3Y + GH + 90)

# ------------------------------------------------------------------ term : tunnel + phrase + isometric rising bars
PH_LINES = ["at the", "highest", "level since"]
PH_F = font(FB, 150)
def phrase_sprite(col):
    lw = [tsize(PH_F, l)[0] for l in PH_LINES]; lh = 170
    im = Image.new("RGBA", (788, lh * 3), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, l in enumerate(PH_LINES):
        bb = PH_F.getbbox(l); d.text(((788 - lw[i]) // 2 - bb[0], i * lh - bb[1] + 10), l, font=PH_F, fill=col + (255,))
    return im.crop((0, 0, 788, lh * 3))
PS_A, PS_B = phrase_sprite(LAV), phrase_sprite(MANGO)
def zoom_phrases(canvas, phase, alpha_mul):
    for i in range(-8, 8):
        n = RR ** (i + phase); s = n * 0.95
        if s < 0.10 or s > 1.0: continue
        a = ease((s - 0.10) / 0.12) * ease((1.0 - s) / 0.16) * 0.55 * alpha_mul
        im = PS_A if i % 2 else PS_B
        w, h = int(im.width * s), int(im.height * s)
        if w < 8: continue
        sp = im.resize((w, h), Image.BILINEAR)
        paste(canvas, sp, SCX - w // 2, 860 - h // 2, alpha=a)

BAR_H = [1, 2, 3, 4, 6, 8]; UNIT = 46
BAR_X0, BAR_Y0 = 300, 1390
def bars_layer(t, tstart):
    lay = IsoLayer(W, 1500, ss=2) if False else IsoLayer(620, 900, ss=2)
    OX, OY = 40, 820                           # layer origin
    cols = [mix(GRAPE, LAV, .55), mix(GRAPE, LAV, .4), mix(GRAPE, LAV, .25), LAV, mix(LAV, MANGO, .35), MANGO]
    for i in range(6):
        p = ease((t - tstart - i * 0.17) / 0.65)
        h = BAR_H[i] * UNIT * p
        if h < 1: h = UNIT * 0.5 * (0.6 + 0.4 * math.sin(t * 6 + i)); cc = mix(DEEP, LAV, .3)
        else: cc = None
        ox, oy = iso_pt2(i * 72, 0, 0, OX, OY)  # base corner
        n = int(h // UNIT); rem = h - n * UNIT
        c = cc or cols[i]
        for j in range(n):
            lay.box(ox, oy, 62, 62, UNIT - 3, j * UNIT, shades(c), iso_pt)
        if rem > 4: lay.box(ox, oy, 62, 62, rem - 3 if rem > 6 else rem, n * UNIT, shades(c), iso_pt)
    return lay.out()
def scene_term(canvas, t):
    tau = t - T_TERM; ph = tunnel_phase(t, T_TERM) + 0.3
    tunnel(canvas, ph)
    late = t >= T_AT - 0.02
    zoom_phrases(canvas, ph, 1.0)
    # CNN context panel (Korean) before the phrase is spoken
    f = font(FB, 56)
    if not late:
        lines = ["CNN: 호르무즈 공격이", "전쟁 이후 최고 수준"]
        pw = 788; ph_ = 270; px = SX0; py = 330 + 20 * (1 - ease(tau / 0.3))
        lay = IsoLayer(pw, ph_); lay.d.rounded_rectangle((0, 0, pw * 2 - 1, ph_ * 2 - 1), 44, fill=DEEP + (255,), outline=MANGO + (255,), width=8)
        im = lay.out(); d = ImageDraw.Draw(im)
        for k, l in enumerate(lines):
            tl = txt_layer(l, f, WHITE if k == 0 else MANGO); im.alpha_composite(tl, ((pw - tl.width) // 2, 52 + k * 92))
        a = ease(tau / 0.3); paste(canvas, im, px, py, alpha=a)
    else:
        # phrase panel: words pop in on their timestamps
        pw, ph_ = 788, 390; px, py = SX0, 306
        lay = IsoLayer(pw, ph_); lay.d.rounded_rectangle((0, 0, pw * 2 - 1, ph_ * 2 - 1), 44, fill=DEEP + (255,), outline=MANGO + (255,), width=8)
        im = lay.out()
        pf = font(FB, 108)
        rows = [[("at", 13), ("the", 14)], [("highest", 15)], [("level", 16), ("since", 17)]]
        # row layout
        for r, row in enumerate(rows):
            sp = 30; ws_ = [tsize(pf, w_)[0] for w_, _ in row]; tot = sum(ws_) + sp * (len(row) - 1); x = (pw - tot) // 2
            for (w_, idx), wd in zip(row, ws_):
                p = (t - words[idx]["s"]) / 0.18
                col = MANGO if w_ == "highest" else WHITE
                if p <= 0:
                    gt = txt_layer(w_, pf, mix(DEEP, LAV, .4)); im.alpha_composite(gt, (x, 34 + r * 114 + (gt.height - gt.height) // 2))
                if p > 0:
                    tl = txt_layer(w_, pf, col); sc = 1 + 0.35 * (1 - eout(p)) if p < 1 else 1
                    tl2 = tl.resize((int(tl.width * sc), int(tl.height * sc)), Image.BILINEAR)
                    im.alpha_composite(tl2, (x + (wd - tl2.width) // 2, 34 + r * 114 + (tl.height - tl2.height) // 2))
                x += wd + sp
        paste(canvas, im, px, py, alpha=ease((t - T_AT + 0.02) / 0.15))
        # rising iso bars
        bl = bars_layer(t, T_HIGHEST - 0.08)
        paste(canvas, bl, 232, 600)
        # 'highest level' flag on tallest bar
        fp = ease((t - T_LEVEL - 0.6) / 0.3)
        if fp > 0:
            ff = font(FB, 46); tl = txt_layer("HIGHEST", ff, DEEP)
            bw, bh = tl.width + 44, 74; fl = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(fl).rounded_rectangle((0, 0, bw - 1, bh - 1), 22, fill=MANGO + (255,)); fl.alpha_composite(tl, (22, (bh - tl.height) // 2))
            paste(canvas, fl, 600 - bw // 2 + 10, 945 - 20 * (1 - fp) , alpha=fp)

# ------------------------------------------------------------------ meaning : halftone gradient wipe onto mango
MEAN_HT = HT(0, 0, W, H, 34, 45)
def scene_mean(canvas, t):
    canvas[:] = MANGO
    # deep halftone gradient from bottom-left (big dots) fading toward top-right, slowly drifting
    f = np.clip(1 - (MEAN_HT.cx / W * 0.55 + (1 - MEAN_HT.cy / H) * 0.9) + 0.06 * np.sin(t * 1.6), 0, 1)
    rad = (f ** 1.1 * 0.62 * 34).astype(np.float32)
    comp(canvas, mix(MANGO, DEEP, .86), MEAN_HT.alpha(rad))
    tau = t - T_MEAN
    # iso stairs echo in the lower-right
    lay = IsoLayer(420, 360)
    for i in range(4):
        p = ease((tau - 0.4 - i * 0.12) / 0.4); h = (i + 1) * 34 * p
        if h > 1:
            ox, oy = iso_pt2(i * 66, 0, 0, 40, 330); lay.box(ox, oy, 60, 60, h, 0, shades(GRAPE if i < 3 else DEEP), iso_pt)
    paste(canvas, lay.out(), 470, 1060)
    # text
    f1 = font(FB, 170); a1 = txt_layer("~ 이후", f1, DEEP); f2 = font(FB, 170); a2 = txt_layer("최고 수준", f2, GRAPE)
    for k, (im, tw) in enumerate(((a1, T_MEAN), (a2, ws(19)))):
        p = ease((t - tw) / 0.28)
        if p > 0: paste(canvas, im, SX0 + 8 + 70 * (1 - p), 520 + k * 230, alpha=p)
    # phrase chip
    chf = font(FB, 44); chl = txt_layer("at the highest level since", chf, MANGO)
    cw, ch_ = chl.width + 50, 84; chip = Image.new("RGBA", (cw, ch_), (0, 0, 0, 0))
    ImageDraw.Draw(chip).rounded_rectangle((0, 0, cw - 1, ch_ - 1), 28, fill=DEEP + (255,)); chip.alpha_composite(chl, (25, (ch_ - chl.height) // 2))
    paste(canvas, chip, SX0, 330, alpha=ease((tau - 0.1) / 0.25))

# ------------------------------------------------------------------ example_en : halftone panel + mango box + big halftone 2008
PANEL = HT(SX0, 306, 788, 640, 16, 45)
G2008 = make_glyph_mask("2008", 330, FB)
G2W, G2H = G2008.size
G2X, G2Y = SX0 + (788 - G2W) // 2 - 0, 1000
G2HT = HT(G2X, G2Y, G2W, G2H, 11, 45)
_g20 = cv2.GaussianBlur(np.asarray(G2008).astype(np.float32) / 255, (0, 0), 4)
_g20col = np.zeros((G2H, G2W, 3), np.float32)
_gy2 = np.linspace(0, 1, G2H)[:, None]
for k in range(3): _g20col[..., k] = MANGO[k] * (1 - _gy2) + LAV[k] * _gy2
def scene_en(canvas, t):
    tau = t - T_EN
    bg_halftone(canvas, t, DEEP, mix(DEEP, GRAPE, .55), wave=1.4)
    # panel with halftone texture (gradient: dots larger toward bottom-right, subtle so text keeps contrast)
    pa = ease(tau / 0.3)
    lay = IsoLayer(788, 640); lay.d.rounded_rectangle((0, 0, 788 * 2 - 1, 640 * 2 - 1), 50, fill=GRAPE + (255,)); mk = np.asarray(lay.out())[..., 3].astype(np.float32) / 255
    pan = np.zeros((640, 788, 3), np.uint8); pan[:] = GRAPE
    f = np.clip((PANEL.cx - SX0) / 788 * 0.5 + (PANEL.cy - 306) / 640 * 0.7 + 0.15 * np.sin(t * 1.2), 0, 1)
    comp(pan, mix(GRAPE, LAV, .17), PANEL.alpha((f * 0.50 * 16).astype(np.float32)))
    im = Image.fromarray(pan).convert("RGBA"); im.putalpha(Image.fromarray((mk * 255).astype(np.uint8)))
    # sentence rows
    pf = font(FB, 92); rows = [[("Prices", 23), ("are", 24)], [("at", 25), ("the", 26), ("highest", 27)], [("level", 28), ("since", 29)], [("2008.", 30)]]
    hl_rows = (1, 2); y = 52; lh = 142; sp = 26
    for r, row in enumerate(rows):
        ws_ = [tsize(pf, w_)[0] for w_, _ in row]; tot = sum(ws_) + sp * (len(row) - 1); x = 52 if r != 0 else 52
        # mango box behind highlighted rows (drawn as soon as first word of row appears)
        if r in hl_rows:
            bp = ease((t - words[row[0][1]]["s"] + 0.04) / 0.22)
            if bp > 0:
                bw = int((tot + 44) * bp); lay2 = IsoLayer(tot + 44, 128)
                lay2.d.rounded_rectangle((0, 0, (tot + 44) * 2 - 1, 128 * 2 - 1), 30, fill=MANGO + (255,))
                bim = lay2.out().crop((0, 0, max(1, bw), 128)); im.alpha_composite(bim, (x - 22, y + r * lh - 8 - 6))
        for (w_, idx), wd in zip(row, ws_):
            p = (t - words[idx]["s"]) / 0.16
            if p <= 0:
                gt = txt_layer(w_, pf, mix(GRAPE, LAV, .4)); im.alpha_composite(gt, (x, y + r * lh + (92 - gt.height) // 2 + 6))
            if p > 0:
                col = DEEP if r in hl_rows else WHITE
                tl = txt_layer(w_, pf, col); dy = int(18 * (1 - eout(p)))
                a = tl.copy(); a.putalpha(a.getchannel("A").point(lambda v: int(v * min(1, p))))
                im.alpha_composite(a, (x, y + r * lh + dy + (92 - tl.height) // 2 + 6))
            x += wd + sp
    paste(canvas, im, SX0, 306 + 24 * (1 - pa), alpha=pa)
    # big halftone 2008
    tp = t - ws(30)
    if True:
        grow = eback(tp / 0.45) if tp < 0.45 else 1.0
        pulse = 1.0 + 0.05 * math.sin(t * 5.5)
        halftone_glyph(canvas, G2HT, _g20, _g20col, G2X, G2Y, t, pulse * (max(grow, 0.01) if tp > -0.02 else 0.35), rmax=0.66)
        pass
    else:
        lbl = None

# ------------------------------------------------------------------ example_ko : lavender, halftone gradient, big stairs
KO_HT = HT(0, 0, W, H, 40, 45)
def scene_ko(canvas, t):
    tau = t - T_KO
    canvas[:] = LAV
    f = np.clip((KO_HT.cy / H) * 1.3 - 0.25 + 0.2 * np.sin(t * 1.4 + KO_HT.cx / 300), 0, 1)
    comp(canvas, mix(LAV, GRAPE, .22), KO_HT.alpha((f * 0.6 * 40).astype(np.float32)))
    pf = fit_font(FB, "최고 수준이에요.", 760, 112, 64)
    rows = [[("물가가", 31)], [("2008년", 32), ("이후", 33)], [("최고", 34), ("수준이에요.", 35)]]
    y0 = 420; lh = int(pf.size * 1.32); sp = int(pf.size * 0.3)
    for r, row in enumerate(rows):
        ws_ = [tsize(pf, w_)[0] for w_, _ in row]; tot = sum(ws_) + sp * (len(row) - 1); x = SX0 + 4
        if r >= 1:
            bp = ease((t - words[row[0][1]]["s"] + 0.03) / 0.22)
            if bp > 0:
                bwid = tot + 40; lay = IsoLayer(bwid, lh - 8)
                lay.d.rounded_rectangle((0, 0, bwid * 2 - 1, (lh - 8) * 2 - 1), 26, fill=MANGO + (255,))
                paste(canvas, lay.out().crop((0, 0, max(1, int(bwid * bp)), lh - 8)), x - 20, y0 + r * lh - 8, alpha=1)
        for (w_, idx), wd in zip(row, ws_):
            p = (t - words[idx]["s"]) / 0.16
            if p <= 0: paste(canvas, txt_layer(w_, pf, mix(LAV, GRAPE, .35)), x, y0 + r * lh + 4)
            if p > 0:
                tl = txt_layer(w_, pf, DEEP); paste(canvas, tl, x, y0 + r * lh + 18 * (1 - eout(p)) + (pf.size - tl.height) // 2 + 4, alpha=min(1, p))
            x += wd + sp
    # English echo
    ef = font(FBD, 44); e = txt_layer("Prices are at the highest level since 2008.", fit_font(FBD, "Prices are at the highest level since 2008.", 788, 44, 30), GRAPE)
    paste(canvas, e, SX0, 1060, alpha=ease((tau - 0.5) / 0.3))
    # rising isometric bars (decor, low)
    lay = IsoLayer(560, 400)
    for i in range(6):
        p = ease((tau - 0.3 - i * 0.1) / 0.5); h = (14 + i * 26) * p
        if h > 1:
            ox, oy = iso_pt2(i * 70, 0, 0, 30, 330); lay.box(ox, oy, 56, 56, h, 0, shades(MANGO if i == 5 else GRAPE), iso_pt)
    paste(canvas, lay.out(), 300, 1105)

# ------------------------------------------------------------------ payoff : zoom out
def scene_pay(canvas, t):
    tau = t - T_PAY
    # zoom-OUT tunnel: phase runs backwards, fast then settling
    ph = 6.0 - (0.9 * tau + 4.0 * (1 - math.exp(-tau / 0.5)))
    tunnel(canvas, ph + 0.0)
    zoom_phrases(canvas, ph, 0.8)
    p = eout(tau / 0.6); sc = 1.9 - 0.9 * p
    f = font(FB, 120); a = txt_layer("저장해 두기", f, WHITE)
    # dark plate for contrast
    pw, ph_ = 788, 250; plate = IsoLayer(pw, ph_); plate.d.rounded_rectangle((0, 0, pw * 2 - 1, ph_ * 2 - 1), 50, fill=DEEP + (255,), outline=MANGO + (255,), width=8)
    pim = plate.out(); pim.alpha_composite(a, ((pw - a.width) // 2, (ph_ - a.height) // 2 - 4))
    paste(canvas, pim, SCX - int(pw * sc) // 2, 560 - int(ph_ * sc) // 2 + 120, alpha=min(1, tau / 0.12 + 0.0001) if tau > 0 else 0, scale=sc)
    f2 = fit_font(FB, "at the highest level since", 690, 52, 34); t2 = txt_layer("at the highest level since", f2, DEEP)
    bw, bh = t2.width + 54, t2.height + 44; box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((0, 0, bw - 1, bh - 1), 24, fill=MANGO + (255,)); box.alpha_composite(t2, (27, 22))
    q = eout((tau - 0.25) / 0.5); sc2 = 1.5 - 0.5 * q
    if tau > 0.25: paste(canvas, box, SCX - int(bw * sc2) // 2, 880 - int(bh * sc2) // 2, alpha=min(1, q * 2), scale=sc2)

# ------------------------------------------------------------------ frame assembly
BIRD_POS = {0: (150, 1500), 1: (150, 1500), 2: (150, 1500), 3: (150, 1500), 4: (150, 1500), 5: (SCX, 1420)}
def beat_index(t):
    for i in range(6):
        if BOUNDS[i] <= t + 1e-6 < BOUNDS[i + 1]: return i
SCENES = [scene_hook, scene_term, scene_mean, scene_en, scene_ko, scene_pay]
HANDLE_FG = [WHITE, WHITE, DEEP, WHITE, DEEP, WHITE]
WIPE_DUR = 0.75
WIPE = HT(0, 0, W, H, 30, 45)
def render_scene(i, t, mouth):
    c = np.zeros((H, W, 3), np.uint8); SCENES[i](c, t)
    return c
def frame(t, env):
    i = beat_index(t); c = render_scene(i, t, 0)
    if i == 2 and t - T_MEAN < WIPE_DUR:       # halftone gradient wipe prev(term) -> meaning
        prev = render_scene(1, t, 0); p = (t - T_MEAN) / WIPE_DUR
        g = np.clip(WIPE.cx / W * 0.75 + (1 - WIPE.cy / H) * 0.25, 0, 1)   # gradient: left->right
        r = np.clip((p * 1.5 - g) * 3.0, 0, 1) * 0.76 * 30
        m = WIPE.alpha(r.astype(np.float32))[..., None]
        c = (prev.astype(np.float32) + (c.astype(np.float32) - prev) * m).astype(np.uint8)
    mo = float(env[min(len(env) - 1, int(t * FPS))])
    cx, by = BIRD_POS[i]
    if i in (1, 2, 3): bird_on_block(canvas=c, mouth=mo, cx=cx, base_y=by, t=t, size=200, blockcol=MANGO if i != 2 else GRAPE)
    elif i == 0: bird_on_block(c, mo, 700 + 0, 1560, t, size=0 or 190, blockcol=MANGO) if False else bird_on_block(c, mo, cx, by, t, size=200)
    else: bird_on_block(c, mo, cx, by, t, size=240 if i == 5 else 200, blockcol=MANGO if i != 4 else GRAPE)
    paste(c, pill_layer(), SX0, 224)
    handle(c, HANDLE_FG[i])
    return c

def check_contrast():
    pairs = {"hook sub (white on deep)": (WHITE, DEEP), "hook 3척 lav on deep": (LAV, DEEP), "3 dots mango on deep": (MANGO, DEEP),
             "CNN panel white on deep": (WHITE, DEEP), "CNN panel mango on deep": (MANGO, DEEP), "phrase highest mango on deep": (MANGO, DEEP),
             "meaning deep on mango": (DEEP, MANGO), "meaning grape on mango": (GRAPE, MANGO), "chip mango on deep": (MANGO, DEEP),
             "example white on grape": (WHITE, GRAPE), "highlight deep on mango": (DEEP, MANGO), "2008 mango on deep": (MANGO, DEEP),
             "ko deep on lavender": (DEEP, LAV), "ko deep on mango box": (DEEP, MANGO), "en echo grape on lavender": (GRAPE, LAV),
             "payoff white on deep": (WHITE, DEEP), "payoff phrase deep on mango": (DEEP, MANGO), "pill deep on mango": (DEEP, MANGO),
             "handle white on deep": (WHITE, DEEP), "handle deep on mango/lav": (DEEP, MANGO)}
    return {k: round(contrast(a, b), 2) for k, (a, b) in pairs.items()}

def mouth_env():
    return BIRD.envelope(MP3, FPS, NF + 2)

def main():
    os.makedirs(FR, exist_ok=True)
    env = mouth_env()
    if "--test" in sys.argv:
        for a in sys.argv[sys.argv.index("--test") + 1:]:
            t = float(a); Image.fromarray(frame(t, env)).save(f"{FR}/test_{a}.png")
        return
    out = f"{OUT}/kw3_{RID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", MP3, "-filter_complex", "[1:a]apad,aformat=channel_layouts=stereo[a]", "-map", "0:v", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "1", "-c:a", "aac", "-b:a", "192k",
           "-ar", "44100", "-t", f"{TOTAL:.3f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(NF): p.stdin.write(frame(k / FPS, env).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg failed")
    marks = {"hook_0.0": 0.0, "hook_0.3": 0.3, "hook_1.0": 1.0, "hook_3.0": 3.0, "term_cnn": 6.0, "term_phrase": 10.2, "meaning": 12.6,
             "example_en": 17.4, "example_ko": 20.6, "payoff": 21.6}
    for k, t in marks.items():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", out, "-frames:v", "1", f"{FR}/kw3_{RID}_{k}.png"], check=True)
    print("done", TOTAL, check_contrast())

if __name__ == "__main__":
    main()
