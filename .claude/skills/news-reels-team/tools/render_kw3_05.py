#!/usr/bin/env python3
"""kw3_05  'at the highest level since'  -- HERO IMAGE: line chart above the 2008 peak; halftone/zoom/iso toned down (card-2 palette).
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


# ------------------------------------------------------------------ HERO IMAGE : line chart "now is above the 2008 peak"
PAYB = [b for b in WK["beats"] if b["role"] == "payoff"][0]
T_EXPR0, T_EXPR1, T_SAVE = PAYB["expr_start"], PAYB["expr_end"], PAYB["save_start"]
CH_PTS = [(0, .30), (.09, .44), (.18, .60), (.26, .70), (.30, .74), (.36, .60), (.44, .42), (.53, .36), (.62, .46),
          (.72, .60), (.82, .74), (.91, .86), (1, .96)]
PK_I = 4; PK_V = CH_PTS[PK_I][1]
def catmull(pts, n=24):
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = [np.array(p, float) for p in P[i - 1:i + 3]]
        for k in range(n):
            s = k / n; out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(np.array(pts[-1], float)); return np.array(out)
CURVE = catmull(CH_PTS)
_seg = np.hypot(np.diff(CURVE[:, 0]) * 788, np.diff(CURVE[:, 1]) * 450)
CUM = np.concatenate([[0], np.cumsum(_seg)]); CUM /= CUM[-1]
PK_FRAC = float(CUM[PK_I * 24])
FIN_T = T_SINCE + 0.85                                   # line reaches the top
def line_prog(t):
    """fraction of the stroke drawn: slow draw through the CNN sentence, peak exactly at 'since', climb after it"""
    if t <= T_TERM + 0.2: return 0.0
    if t < T_SINCE:
        a = [(T_TERM + 0.2, 0.0), (T_AT, 0.55 * PK_FRAC), (T_SINCE, PK_FRAC)]
        for (t0, v0), (t1, v1) in zip(a, a[1:]):
            if t < t1: return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return PK_FRAC + (1 - PK_FRAC) * ease((t - T_SINCE) / 0.85)

def ctext(lay, s, size, cx, cy, fill):
    ImageDraw.Draw(lay.im).text((cx * lay.ss, cy * lay.ss), s, font=font(FB, int(size * lay.ss)), fill=fill + (255,), anchor="mm")

def chart_layer(w, h, t, label, fs, chip_hi=False, pulses=()):
    lay = IsoLayer(w, h); S = lay.ss; d = lay.d
    d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), 40 * S, fill=DEEP + (255,), outline=LAV + (255,), width=3 * S)
    pl, pr, pt, pb = 0.07 * w, 0.10 * w, 0.34 * h, 0.13 * h
    X = lambda u: (pl + u * (w - pl - pr)) * S
    Y = lambda v: (h - pb - v * (h - pb - pt)) * S
    # grid + baseline (quiet)
    for g in (.25, .5, .75, 1.0): d.line([(pl * S, Y(g)), ((w - pr * .4) * S, Y(g))], fill=mix(DEEP, LAV, .14) + (255,), width=S * 2)
    d.line([(pl * S, Y(0)), ((w - pr * .4) * S, Y(0))], fill=mix(DEEP, LAV, .6) + (255,), width=S * 3)
    ctext(lay, "시간 →", max(22, fs * 0.55), w - pr * .4 - fs * 1.1, h - pb * 0.45, mix(DEEP, LAV, .85))
    lp = line_prog(t); m = int(np.searchsorted(CUM, lp))
    if lp > 0.002:
        idx = min(m, len(CURVE) - 1); pts = [(X(u), Y(v)) for u, v in CURVE[:idx]]
        if idx < len(CURVE):
            a, b = CUM[idx - 1], CUM[idx]; f = (lp - a) / max(1e-9, b - a)
            q = CURVE[idx - 1] + (CURVE[idx] - CURVE[idx - 1]) * f; pts.append((X(q[0]), Y(q[1])))
        if len(pts) >= 2:
            d.polygon(pts + [(pts[-1][0], Y(0)), (pts[0][0], Y(0))], fill=mix(DEEP, GRAPE, .8) + (255,))
            d.line([(pl * S, Y(0)), ((w - pr * .4) * S, Y(0))], fill=mix(DEEP, LAV, .6) + (255,), width=S * 3)
            lw = max(6, int(round(w * 0.0125))) * S
            d.line(pts, fill=MANGO + (255,), width=lw, joint="curve")
            for (px_, py_) in (pts[0], pts[-1]): d.ellipse([px_ - lw / 2, py_ - lw / 2, px_ + lw / 2, py_ + lw / 2], fill=MANGO + (255,))
    # dashed previous-peak line "2008"
    tp = t - T_SINCE
    ypk = Y(PK_V)
    if tp >= 0:
        dp = ease(tp / 0.45); x_end = X(0) + (X(1) + 0.03 * w * S - X(0)) * dp; x = X(0)
        while x < x_end:
            d.line([(x, ypk), (min(x + 16 * S, x_end), ypk)], fill=LAV + (255,), width=S * 3); x += 28 * S
        cf = font(FB, int(fs * 0.85 * S)); tw_ = d.textlength("2008", font=cf) / S
        cw_, ch_ = tw_ + 30, fs * 0.85 * 1.55
        cx0, cy0 = pl + 6, ypk / S - ch_ - 8
        d.rounded_rectangle((cx0 * S, cy0 * S, (cx0 + cw_) * S, (cy0 + ch_) * S), int(ch_ * .4 * S), fill=(MANGO if chip_hi else LAV) + (255,))
        ctext(lay, "2008", fs * 0.85, cx0 + cw_ / 2, cy0 + ch_ / 2 + 1, DEEP)
        # peak dot pops at 'since'
        k = eback(tp / 0.30); r = 0.024 * w * k
        pxk, pyk = X(CH_PTS[PK_I][0]), Y(PK_V)
        d.ellipse([pxk - r * S, pyk - r * S, pxk + r * S, pyk + r * S], fill=MANGO + (255,), outline=WHITE + (255,), width=S * 3)
        for pt0 in list(pulses) + [T_SINCE]:
            q = (t - pt0) / 0.6
            if 0 < q < 1:
                rr = (0.024 + 0.06 * q) * w * S; d.ellipse([pxk - rr, pyk - rr, pxk + rr, pyk + rr], outline=mix(DEEP, WHITE, 1 - q) + (255,), width=S * 3)
    # latest point: pulsing dot, up-arrow, label
    if t >= FIN_T:
        xf, yf = X(1), Y(CH_PTS[-1][1]); fq = t - FIN_T
        r = 0.032 * w * (eback(fq / 0.3) if fq < 0.3 else 1 + 0.10 * math.sin(t * 7))
        q = (fq % 1.1) / 1.1; rr = (0.032 + 0.07 * q) * w * S
        d.ellipse([xf - rr, yf - rr, xf + rr, yf + rr], outline=mix(DEEP, MANGO, 1 - q) + (255,), width=S * 3)
        d.ellipse([xf - r * S, yf - r * S, xf + r * S, yf + r * S], fill=MANGO + (255,), outline=WHITE + (255,), width=S * 4)
        ah = min(0.20 * h, (yf / S) - 0.06 * h - r) * ease(fq / 0.35); y0 = yf - r * S - 6 * S; y1 = y0 - ah * S
        aw = fs * 0.42 * S
        d.line([(xf, y0), (xf, y1 + aw)], fill=WHITE + (255,), width=int(0.011 * w * S))
        d.polygon([(xf, y1), (xf - aw * .8, y1 + aw * 1.3), (xf + aw * .8, y1 + aw * 1.3)], fill=WHITE + (255,))
        lf = font(FB, int(fs * S)); lw_ = d.textlength(label, font=lf) / S; ch_ = fs * 1.6; cw_ = lw_ + 44
        cx1 = min(xf / S - aw / S * 1.6 - cw_, w - 20 - cw_); cx1 = xf / S - 0.07 * w - cw_ + 0.01 * w
        cy1 = 0.05 * h + 4
        d.rounded_rectangle((cx1 * S, cy1 * S, (cx1 + cw_) * S, (cy1 + ch_) * S), int(ch_ * .38 * S), fill=MANGO + (255,))
        ctext(lay, label, fs, cx1 + cw_ / 2, cy1 + ch_ / 2 + 1, DEEP)
    return lay.out()

def chart(canvas, t, x, y, w, h, label, fs, a=1.0, **kw):
    paste(canvas, chart_layer(w, h, t, label, fs, **kw), x, y, alpha=a)

def tunnel_soft(canvas, ph, k=0.62):
    tunnel(canvas, ph); canvas[:] = (canvas.astype(np.float32) * (1 - k) + np.array(DEEP, np.float32) * k).astype(np.uint8)

def rrect(w, h, r, fill, outline=None, ow=0):
    lay = IsoLayer(w, h); lay.d.rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), r * 2, fill=fill + (255,), outline=(outline + (255,)) if outline else None, width=ow * 2)
    return lay.out()

# ------------------------------------------------------------------ term : calm tunnel + sentence + chart draws itself
def scene_term(canvas, t):
    tau = t - T_TERM; ph = tunnel_phase(t, T_TERM) + 0.3
    tunnel_soft(canvas, ph)
    pw = 788
    if t < T_AT - 0.02:
        ph_ = 250; im = rrect(pw, ph_, 44, DEEP, MANGO, 4); f = font(FB, 56)
        for k, l in enumerate(["CNN: 호르무즈 공격이", "전쟁 이후 최고 수준"]):
            tl = txt_layer(l, f, WHITE if k == 0 else MANGO); im.alpha_composite(tl, ((pw - tl.width) // 2, 44 + k * 94))
        paste(canvas, im, SX0, 306 + 16 * (1 - ease(tau / 0.3)), alpha=ease(tau / 0.3))
    else:
        ph_ = 270; im = rrect(pw, ph_, 44, DEEP, MANGO, 4)
        pf = fit_font(FB, "at the highest", 700, 112, 60)
        rows = [[("at", 13), ("the", 14), ("highest", 15)], [("level", 16), ("since", 17)]]
        for r, row in enumerate(rows):
            sp = 26; wsx = [tsize(pf, w_)[0] for w_, _ in row]; x = (pw - sum(wsx) - sp * (len(row) - 1)) // 2
            for (w_, idx), wd in zip(row, wsx):
                p = (t - words[idx]["s"]) / 0.18; col = MANGO if w_ == "highest" else WHITE
                if p <= 0: im.alpha_composite(txt_layer(w_, pf, mix(DEEP, LAV, .45)), (x, 28 + r * 120))
                else:
                    tl = txt_layer(w_, pf, col); sc = 1 + 0.3 * (1 - eout(p)) if p < 1 else 1
                    t2 = tl.resize((int(tl.width * sc), int(tl.height * sc)), Image.BILINEAR)
                    im.alpha_composite(t2, (x + (wd - t2.width) // 2, 28 + r * 120 + (tl.height - t2.height) // 2))
                x += wd + sp
        paste(canvas, im, SX0, 306, alpha=ease((t - T_AT + 0.02) / 0.15))
    chart(canvas, t, SX0, 610, 788, 640, "지금 = 최고 수준", 50, a=ease(tau / 0.35))

# ------------------------------------------------------------------ meaning : mango, soft halftone, chart small up top
MEAN_HT = HT(0, 0, W, H, 34, 45)
def scene_mean(canvas, t):
    canvas[:] = MANGO
    f = np.clip(1 - (MEAN_HT.cx / W * 0.55 + (1 - MEAN_HT.cy / H) * 0.9) + 0.06 * np.sin(t * 1.6), 0, 1)
    comp(canvas, mix(MANGO, DEEP, .24), MEAN_HT.alpha((f ** 1.1 * 0.50 * 34).astype(np.float32)))
    tau = t - T_MEAN
    chf = font(FB, 44); chl = txt_layer("at the highest level since", chf, MANGO)
    cw, ch_ = chl.width + 50, 84; chip = rrect(cw, ch_, 28, DEEP); chip.alpha_composite(chl, (25, (ch_ - chl.height) // 2))
    paste(canvas, chip, SX0, 310, alpha=ease((tau - 0.05) / 0.25))
    chart(canvas, t, SX0, 430, 788, 400, "지금 = 최고 수준", 40)
    f1 = font(FB, 160); a1 = txt_layer("~ 이후", f1, DEEP); a2 = txt_layer("최고 수준", f1, GRAPE)
    for k, (im, tw) in enumerate(((a1, T_MEAN), (a2, ws(19)))):
        p = ease((t - tw) / 0.28)
        if p > 0: paste(canvas, im, SX0 + 8 + 70 * (1 - p), 900 + k * 210, alpha=p)

# ------------------------------------------------------------------ example_en : chart small + sentence panel
def scene_en(canvas, t):
    tau = t - T_EN
    bg_halftone(canvas, t, DEEP, mix(DEEP, GRAPE, .55), strength=0.55, wave=1.4)
    chart(canvas, t, SX0, 300, 788, 340, "2008 이후 최고", 40, chip_hi=(t >= ws(30)), pulses=[ws(30)])
    pa = ease(tau / 0.3); pw, ph_ = 788, 580
    im = rrect(pw, ph_, 50, GRAPE)
    pf = font(FB, 84); rows = [[("Prices", 23), ("are", 24)], [("at", 25), ("the", 26), ("highest", 27)], [("level", 28), ("since", 29)], [("2008.", 30)]]
    hl_rows = (1, 2); y = 40; lh = 130; sp = 24
    for r, row in enumerate(rows):
        wsx = [tsize(pf, w_)[0] for w_, _ in row]; tot = sum(wsx) + sp * (len(row) - 1); x = 52
        if r in hl_rows:
            bp = ease((t - words[row[0][1]]["s"] + 0.04) / 0.22)
            if bp > 0:
                bim = rrect(tot + 44, 118, 30, MANGO).crop((0, 0, max(1, int((tot + 44) * bp)), 118)); im.alpha_composite(bim, (x - 22, y + r * lh - 4))
        for (w_, idx), wd in zip(row, wsx):
            p = (t - words[idx]["s"]) / 0.16
            if p <= 0: gt = txt_layer(w_, pf, mix(GRAPE, LAV, .45)); im.alpha_composite(gt, (x, y + r * lh + (84 - gt.height) // 2 + 10))
            else:
                tl = txt_layer(w_, pf, DEEP if r in hl_rows else WHITE); dy = int(16 * (1 - eout(p)))
                a = tl.copy(); a.putalpha(a.getchannel("A").point(lambda v: int(v * min(1, p))))
                im.alpha_composite(a, (x, y + r * lh + dy + (84 - tl.height) // 2 + 10))
            x += wd + sp
    paste(canvas, im, SX0, 668 + 20 * (1 - pa), alpha=pa)

# ------------------------------------------------------------------ example_ko : lavender, chart small + translation
KO_HT = HT(0, 0, W, H, 40, 45)
def scene_ko(canvas, t):
    tau = t - T_KO
    canvas[:] = LAV
    f = np.clip((KO_HT.cy / H) * 1.3 - 0.25 + 0.2 * np.sin(t * 1.4 + KO_HT.cx / 300), 0, 1)
    comp(canvas, mix(LAV, GRAPE, .16), KO_HT.alpha((f * 0.45 * 40).astype(np.float32)))
    chart(canvas, t, SX0, 300, 788, 340, "2008 이후 최고", 40, chip_hi=(t >= ws(32)), pulses=[ws(32)])
    pf = fit_font(FB, "최고 수준이에요.", 740, 104, 64)
    rows = [[("물가가", 31)], [("2008년", 32), ("이후", 33)], [("최고", 34), ("수준이에요.", 35)]]
    y0 = 690; lh = int(pf.size * 1.32); sp = int(pf.size * 0.3)
    for r, row in enumerate(rows):
        wsx = [tsize(pf, w_)[0] for w_, _ in row]; tot = sum(wsx) + sp * (len(row) - 1); x = SX0 + 4
        if r >= 1:
            bp = ease((t - words[row[0][1]]["s"] + 0.03) / 0.22)
            if bp > 0:
                bwid = tot + 40
                paste(canvas, rrect(bwid, lh - 8, 26, MANGO).crop((0, 0, max(1, int(bwid * bp)), lh - 8)), x - 20, y0 + r * lh - 8, alpha=1)
        for (w_, idx), wd in zip(row, wsx):
            p = (t - words[idx]["s"]) / 0.16
            if p <= 0: paste(canvas, txt_layer(w_, pf, mix(LAV, GRAPE, .4)), x, y0 + r * lh + 4)
            else:
                tl = txt_layer(w_, pf, DEEP); paste(canvas, tl, x, y0 + r * lh + 18 * (1 - eout(p)) + (pf.size - tl.height) // 2 + 4, alpha=min(1, p))
            x += wd + sp
    e = txt_layer("Prices are at the highest level since 2008.", fit_font(FBD, "Prices are at the highest level since 2008.", 788, 42, 30), GRAPE)
    paste(canvas, e, SX0, 1130, alpha=ease((tau - 0.5) / 0.3))

# ------------------------------------------------------------------ payoff : expression big (highlight while spoken) + chart small + save pop
def scene_pay(canvas, t):
    tau = t - T_PAY
    ph = 6.0 - (0.9 * tau + 4.0 * (1 - math.exp(-tau / 0.5)))
    tunnel_soft(canvas, ph, 0.70)
    chart(canvas, t, SX0, 300, 788, 330, "2008 이후 최고", 40, chip_hi=True, pulses=[T_EXPR1 - 0.4])
    pw, ph_ = 788, 340; pa = ease(tau / 0.2)
    im = rrect(pw, ph_, 50, DEEP, MANGO, 5); pf = fit_font(FB, "at the highest", 700, 118, 60)
    rows = [[("at", 36), ("the", 37), ("highest", 38)], [("level", 39), ("since.", 40)]]
    for r, row in enumerate(rows):
        sp = 28; wsx = [tsize(pf, w_)[0] for w_, _ in row]; x = (pw - sum(wsx) - sp * (len(row) - 1)) // 2
        for (w_, idx), wd in zip(row, wsx):
            s_, e_ = words[idx]["s"], words[idx]["e"]; yy = 44 + r * 140
            if t < s_: im.alpha_composite(txt_layer(w_, pf, mix(DEEP, LAV, .45)), (x, yy))
            elif t <= e_ + 0.06:
                tl = txt_layer(w_, pf, DEEP); bx = rrect(wd + 36, tl.height + 30, 26, MANGO)
                pp = eout((t - s_) / 0.15); sc = 1 + 0.12 * (1 - pp)
                bx = bx.resize((int(bx.width * sc), int(bx.height * sc)), Image.BILINEAR)
                im.alpha_composite(bx, (x - 18 - (bx.width - wd - 36) // 2, yy - 15 - (bx.height - tl.height - 30) // 2)); im.alpha_composite(tl, (x, yy))
            else: im.alpha_composite(txt_layer(w_, pf, WHITE), (x, yy))
            x += wd + sp
    paste(canvas, im, SX0, 670, alpha=pa)
    # save element
    sq = (t - T_SAVE) / 0.4
    if sq > 0:
        k = eback(sq) if sq < 1 else 1 + 0.03 * math.sin((t - T_SAVE) * 6)
        sw, sh = 640, 150; pill = rrect(sw, sh, 75, MANGO, WHITE, 4)
        f = font(FB, 78); tl = txt_layer("저장해 두기", f, DEEP)
        lay = IsoLayer(70, 90); lay.poly([(8, 8), (62, 8), (62, 84), (35, 62), (8, 84)], DEEP); bm = lay.out()
        tot = bm.width + 26 + tl.width; x0 = (sw - tot) // 2
        pill.alpha_composite(bm, (x0, (sh - bm.height) // 2)); pill.alpha_composite(tl, (x0 + bm.width + 26, (sh - tl.height) // 2 - 2))
        paste(canvas, pill, SX0 + (788 - sw) // 2 + (sw - int(sw * k)) // 2, 1065 + (sh - int(sh * k)) // 2, alpha=min(1, sq * 3), scale=k)
        if sq < 1.2:
            lay = IsoLayer(788, 200)
            for j in range(8):
                a_ = j * math.pi / 4; rr = 20 + 60 * min(1, sq); lay.d.line([(394 * 2 + rr * 2 * math.cos(a_) * 3.2, 100 * 2 + rr * 2 * math.sin(a_)), (394 * 2 + (rr + 24) * 2 * math.cos(a_) * 3.2, 100 * 2 + (rr + 24) * 2 * math.sin(a_))], fill=WHITE + (int(255 * max(0, 1 - sq)),), width=6)

# ------------------------------------------------------------------ frame assembly
BIRD_POS = {i: (150, 1500) for i in range(6)}
def beat_index(t):
    for i in range(6):
        if BOUNDS[i] <= t + 1e-6 < BOUNDS[i + 1]: return i
SCENES = [scene_hook, scene_term, scene_mean, scene_en, scene_ko, scene_pay]
HANDLE_FG = [WHITE, WHITE, DEEP, WHITE, DEEP, WHITE]
WIPE_DUR = 0.75
WIPE = HT(0, 0, W, H, 30, 45)
def render_scene(i, t):
    c = np.zeros((H, W, 3), np.uint8); SCENES[i](c, t); return c
def frame(t, env):
    i = beat_index(t); c = render_scene(i, t)
    if i == 2 and t - T_MEAN < WIPE_DUR:
        prev = render_scene(1, t); p = (t - T_MEAN) / WIPE_DUR
        g = np.clip(WIPE.cx / W * 0.75 + (1 - WIPE.cy / H) * 0.25, 0, 1)
        m = WIPE.alpha((np.clip((p * 1.5 - g) * 3.0, 0, 1) * 0.76 * 30).astype(np.float32))[..., None]
        c = (prev.astype(np.float32) + (c.astype(np.float32) - prev) * m).astype(np.uint8)
    mo = float(env[min(len(env) - 1, int(t * FPS))]); cx, by = BIRD_POS[i]
    bird_on_block(c, mo, cx, by, t, size=200, blockcol=MANGO if i not in (2, 4) else GRAPE)
    paste(c, pill_layer(), SX0, 224)
    handle(c, HANDLE_FG[i])
    return c

def check_contrast():
    mt = mix(MANGO, DEEP, .24)
    pairs = {"hook sub (white on deep)": (WHITE, DEEP), "hook 3척 lav on deep": (LAV, DEEP), "3 dots mango on deep": (MANGO, DEEP),
             "term panel white on deep": (WHITE, DEEP), "term panel mango on deep": (MANGO, DEEP), "term ghost words lav45 on deep (placeholder)": (mix(DEEP, LAV, .45), DEEP),
             "chart line mango on deep": (MANGO, DEEP), "chart line mango on grape fill": (MANGO, mix(DEEP, GRAPE, .8)),
             "chart dashed lav on deep": (LAV, DEEP), "chart chip 2008 deep on lav": (DEEP, LAV), "chart chip label deep on mango": (DEEP, MANGO),
             "chart 시간 label": (mix(DEEP, LAV, .85), DEEP),
             "meaning deep on mango": (DEEP, MANGO), "meaning deep on halftone dot": (DEEP, mt), "meaning grape on mango": (GRAPE, MANGO), "meaning grape on dot": (GRAPE, mt),
             "chip mango on deep": (MANGO, DEEP), "example white on grape": (WHITE, GRAPE), "highlight deep on mango": (DEEP, MANGO),
             "ko deep on lavender": (DEEP, LAV), "ko deep on mango box": (DEEP, MANGO), "en echo grape on lavender": (GRAPE, LAV),
             "payoff white on deep": (WHITE, DEEP), "payoff spoken deep on mango": (DEEP, MANGO), "save deep on mango": (DEEP, MANGO),
             "pill deep on mango": (DEEP, MANGO), "handle white on deep": (WHITE, DEEP)}
    return {k: round(contrast(a, b), 2) for k, (a, b) in pairs.items()}

def mouth_env(): return BIRD.envelope(MP3, FPS, NF + 2)

def main():
    os.makedirs(FR, exist_ok=True); env = mouth_env()
    if "--test" in sys.argv:
        for a in sys.argv[sys.argv.index("--test") + 1:]:
            Image.fromarray(frame(float(a), env)).save(f"{FR}/test_{a}.png")
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
    marks = {"hook_0.0": 0.0, "hook_0.3": 0.3, "hook_1.0": 1.0, "term_cnn": 6.0, "term_draw": 9.2, "term_peak": 9.8, "term_full": 11.0 - 0.4,
             "meaning": 12.6, "example_en": 17.2, "example_ko": 20.6, "payoff_before_save": 23.5, "payoff_after_save": 24.4}
    for k, t in marks.items():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", out, "-frames:v", "1", f"{FR}/kw3_{RID}_{k}.png"], check=True)
    print("done", TOTAL, check_contrast())

if __name__ == "__main__":
    main()
