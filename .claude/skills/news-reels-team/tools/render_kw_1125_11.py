#!/usr/bin/env python3
"""1125 kw_11 'technically' - NEO-BRUTALISM + SHAPE MORPH (prison bars -> room) + a little kinetic type.
Hook type POV. Palette: card 1 Charcoal / Warm White / Performance Orange + hot yellow accent.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw_1125_11.py [--frames]"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird as BIRD

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
RID = "11"
OUT = f"{ROOT}/06_keyword_reels"; FR = f"{OUT}/frames"
MP3 = f"{ROOT}/audio/kw_{RID}.mp3"
W, H, FPS, TAIL = 1080, 1920, 30, 0.7
BLACK_F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
BOLD_F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def hx(s): s = s.lstrip("#"); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
CH, WH, OR, YEL = hx("121212"), hx("FDF9EA"), hx("FE5105"), hx("FFE500")
BLK = (0, 0, 0)
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

WK = json.load(open(f"{ROOT}/audio/words_kw.json"))[RID]
words = WK["words"]; BT = [b["start"] for b in WK["beats"]]
def ws(i): return words[i]["s"]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3],
                           capture_output=True, text=True).stdout)
TOTAL = round((dur + TAIL) * FPS) / FPS
BG = [OR, OR, CH, CH, WH, YEL]                 # per beat
LINE = [CH, CH, OR, OR, CH, CH]                # room/bar colour per beat
PLAT_COL = [YEL, WH, YEL, OR, YEL, OR]

# ---------- stickers (thick outline + hard offset shadow) ----------
def ease_back(p, c1=1.70158):
    q = p - 1; return 1 + (c1 + 1) * q ** 3 + c1 * q ** 2
class Sticker:
    def __init__(s, w, h, bg=None, lines=(), size=0, fg=CH, ol=8, sh=12, angle=0.0, fpath=BLACK_F, lh=1.18, tail=False, pad=None, shc=BLK):
        s.angle = angle; k = 2; pad = pad or (ol + sh + 4)
        if tail: pad = max(pad, 96)
        im = Image.new("RGBA", ((w + 2 * pad) * k, (h + 2 * pad) * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        box = (pad * k, pad * k, (pad + w) * k, (pad + h) * k)
        if bg is not None:
            ob = (box[0] - ol * k, box[1] - ol * k, box[2] + ol * k, box[3] + ol * k)
            d.rectangle(tuple(v + sh * k for v in ob), fill=shc); d.rectangle(ob, fill=BLK); d.rectangle(box, fill=bg)
            if tail:
                x0 = pad + 46; y0 = pad + h
                tri = lambda o: [((x0 - o) * k, (y0 - 4) * k), ((x0 + 8 - o * .2) * k, (y0 + 74 + o) * k), ((x0 + 84 + o) * k, (y0 - 4) * k)]
                d.polygon(tri(ol), fill=BLK); d.polygon(tri(0), fill=bg)
                d.rectangle(((x0 + 2) * k, (y0 - ol - 1) * k, (x0 + 78) * k, (y0 + 1) * k), fill=bg)
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
        if len(s._c) < 300: s._c[key] = out
        return out
def measure(text, size, fpath=BLACK_F): return font(size, fpath).getlength(text)
def block(text, size, fg, bg, angle=0, padx=34, pady=18, **kw):
    w = int(measure(text, size)) + 2 * padx; h = int(size * 1.18) + 2 * pady
    return Sticker(w, h, bg, [text], size, fg, angle=angle, **kw)
def words_sprite(text, size, fg):
    w = int(measure(text, size)) + 8; return Sticker(w, int(size * 1.2), None, [text], size, fg, ol=0, sh=0)

class El:
    def __init__(s, spr, cx, cy, t0, s0=2.0, rot0=10, idle=1.0, ph=0.0, t1=1e9, ghost=None, dur=0.3):
        s.spr, s.cx, s.cy, s.t0, s.s0, s.rot0, s.idle, s.ph, s.t1, s.ghost, s.dur = spr, cx, cy, t0, s0, rot0, idle, ph, t1, ghost, dur
def draw_el(img, e, t):
    if t >= e.t1: return
    if t < e.t0:
        if e.ghost is not None:
            g = e.ghost.get(1.0, round(3 * math.sin(t * 17 + e.ph), 1))
            img.paste(g, (int(e.cx + 5 * math.sin(t * 23 + e.ph) - g.width / 2), int(e.cy + 4 * math.sin(t * 19 + e.ph * 2) - g.height / 2)), g)
        return
    p = (t - e.t0) / e.dur
    if p >= 1: sc, ex, a = 1.0, 0.0, 1.0
    else:
        eb = ease_back(max(0, p)); sc = e.s0 + (1 - e.s0) * eb; ex = e.rot0 * (1 - min(1, p)) ** 2; a = min(1, p * 8)
    dy = e.idle * 3 * math.sin(t * 3.1 + e.ph) if e.idle else 0
    if e.idle and p >= 1: ex += e.idle * 1.2 * math.sin(t * 2.3 + e.ph)
    sp = e.spr.get(sc, ex if p < 1 else round(ex, 1))
    if a < 1: sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v: int(v * a)))
    img.paste(sp, (int(e.cx - sp.width / 2), int(e.cy + dy - sp.height / 2)), sp)
def ghostof(txt, size, ang, fg=(70, 50, 40), bg=WH, **kw):
    g = block(txt, size, fg, bg, ang, **kw)
    g.src.putalpha(g.src.getchannel("A").point(lambda v: int(v * 0.5))); return g

# ---------- beats ----------
ELS = [[] for _ in range(6)]
STACK = []  # (cx, cy, w, h) of term ghost frames
def hook():
    E = ELS[0]; size = 112
    rows = [[("POV:", CH, YEL, 0 - .1, -3, WH)],
            [("친구가", CH, WH, ws(1), 2, None), ("내", CH, WH, ws(2), -3, None)],
            [("방을", CH, WH, ws(3), -2, None), ("감옥", WH, CH, ws(4), 3, None)],
            [("같다고", CH, WH, ws(5), 2, None), ("할", CH, YEL, ws(6), -3, None), ("때.", CH, WH, ws(7), 3, None)]]
    def row_w(r): return sum(measure(x[0], size) + 68 for x in r) + 22 * (len(r) - 1)
    while max(row_w(r) for r in rows) > 770: size -= 4
    y = 400 + size * .6; xs0 = [70, 84, 66, 70]
    for ri, r in enumerate(rows):
        x = xs0[ri]
        for (txt, fg, bg, t0, ang, _) in r:
            wb = measure(txt, size) + 68
            spr = block(txt, size, fg, bg, ang); gh = ghostof(txt, size, ang)
            E.append(El(spr, x + wb / 2, y, t0, 2.1, ang * 3, ph=ri * 3 + x, ghost=gh)); x += wb + 22
        y += int(size * 1.18) + 36 + 14
    # friend's chat bubble (derived from hook only)
    b = Sticker(420, 190, WH, ["야 네 방", "감옥 같아"], 66, CH, angle=-2, tail=True, ol=8, sh=12)
    E.append(El(b, 62 + 10 + b.w / 2 + 12, 1275, -0.1, 1.7, -8, idle=1.5, dur=0.28))
    E.append(El(block("친구", 40, WH, CH, -4, padx=22, pady=8, ol=6, sh=8), 150, 1135, -0.1, 1.6, 8))
def term():
    E = ELS[1]; t0 = BT[1]; t5 = ws(10)
    # typing bubble while "그의 답은," is spoken (dots drawn in frame)
    tb = Sticker(250, 120, WH, ol=8, sh=12, tail=True, angle=2)
    E.append(El(tb, 250, 600, t0, 1.7, -8, t1=t5, dur=0.25))
    rows = [("tech", 165, WH, CH, 70, -3, ws(10)), ("nic", 165, YEL, CH, 150, 2.5, ws(10) + .1), ("ally", 165, CH, WH, 60, -2, ws(10) + .2)]
    y = 350
    for txt, size, bg, fg, xo, ang, t in rows:
        while measure(txt, size) + 90 > 770 - xo: size -= 4
        w = measure(txt, size) + 90; h = size * 1.18 + 56; cx = 62 + 14 + xo + w / 2; cy = y + h / 2
        spr = block(txt, size, fg, bg, ang, padx=45, pady=28, ol=10, sh=16)
        gh = ghostof(txt, size, ang, padx=45, pady=28, ol=10, sh=16)
        E.append(El(spr, cx, cy, t, 2.2, ang * -4, ph=y, ghost=gh, dur=0.26)); y += int(h) + 26
    E.append(El(block("well, actually", 54, CH, YEL, -5, padx=30, pady=14, ol=8, sh=12), 330, 1310, ws(10) + .45, 2.0, 14))
def meaning():
    E = ELS[2]; t0 = BT[2]
    E.append(El(block("뜻", 60, CH, YEL, -4, padx=36, pady=12), 140, 370, t0, 1.8, -10))
    E.append(El(block("technically", 52, WH, OR, 3, padx=26, pady=10, ol=7, sh=10, shc=BLK), 520, 372, t0 + .05, 1.6, 6))
    E.append(El(block("엄밀히", 134, CH, WH, -2, padx=40, pady=20, ol=10, sh=16), 420, 805, ws(15), 2.2, 12))
    E.append(El(block("말하면", 134, CH, WH, 2, padx=40, pady=20, ol=10, sh=16), 440, 1005, ws(16), 2.2, -12))
def panel_text(E, lines, hl_rows, size, x0, y0, idx0, lh, fg, hl_bg, hl_fg, hl_pad=16):
    k = idx0; toks = []
    for ln in lines:
        row = []
        for _ in ln: row.append(k); k += 1
        toks.append(row)
    sp_w = measure(" ", size)
    rw = lambda r: sum(measure(t, size) for t in r) + sp_w * (len(r) - 1)
    hl = sorted(hl_rows); out_y = []; shift = 0
    for r in range(len(lines)):
        if hl and r == hl[0]: shift += hl_pad
        out_y.append(y0 + lh * (r + .5) + shift)
        if hl and r == hl[-1]: shift += hl_pad
    if hl:
        bw = max(rw(lines[r]) for r in hl) + 2 * hl_pad + 8
        top = out_y[hl[0]] - lh / 2 - hl_pad * .4; bot = out_y[hl[-1]] + lh / 2 + hl_pad * .4
        E.append(El(Sticker(int(bw), int(bot - top), hl_bg, ol=8, sh=10), x0 + 8 + bw / 2, (top + bot) / 2, ws(toks[hl[0]][0]) - .05, 1.5, 4, idle=0))
    for r, ln in enumerate(lines):
        x = x0 + (hl_pad + 4 if r in hl else 0)
        for tk, ix in zip(ln, toks[r]):
            w = measure(tk, size); col = hl_fg if r in hl else fg
            E.append(El(words_sprite(tk, size, col), x + w / 2, out_y[r], ws(ix), 1.7, 8, idle=0)); x += w + sp_w
    return out_y[-1] + lh / 2
def example_en():
    E = ELS[3]; t0 = BT[3]; lines = [["Technically,"], ["the", "shop"], ["opens", "at"], ["nine."]]
    size = 92
    while max(sum(measure(t, size) for t in l) + measure(" ", size) * (len(l) - 1) for l in lines) > 640: size -= 4
    lh = int(size * 1.25); pw = 780; px, py = 62, 420; ph = lh * 4 + 32 + 110
    E.append(El(Sticker(pw, ph, WH, ol=10, sh=16, angle=0), px + pw / 2 + 10, py + ph / 2, t0, 1.35, 3, idle=0))
    E.append(El(block("예문", 58, CH, YEL, -4, padx=30, pady=10), 190, py - 12, t0 + .04, 1.8, -10))
    panel_text(E, lines, [0], size, px + 50, py + 70, 19, lh, CH, OR, CH, hl_pad=14)
def example_ko():
    E = ELS[4]; t0 = BT[4]; lines = [["엄밀히", "말하면"], ["그", "가게는"], ["9시에"], ["연다."]]
    size = 92
    while max(sum(measure(t, size) for t in l) + measure(" ", size) * (len(l) - 1) for l in lines) > 640: size -= 4
    lh = int(size * 1.25); pw = 780; px, py = 62, 420; ph = lh * 4 + 32 + 110
    E.append(El(Sticker(pw, ph, CH, ol=10, sh=16, shc=OR), px + pw / 2 + 10, py + ph / 2, t0, 1.35, -3, idle=0))
    E.append(El(block("해석", 58, WH, OR, 4, padx=30, pady=10), 190, py - 12, t0 + .04, 1.8, 10))
    panel_text(E, lines, [0], size, px + 50, py + 70, 25, lh, WH, YEL, CH, hl_pad=14)
def payoff():
    E = ELS[5]; t0 = BT[5]
    rows = [("tech", WH, CH, 70, -3), ("nic", OR, CH, 130, 2.5), ("ally", CH, WH, 60, -2)]
    y = 320; size = 150
    for i, (txt, bg, fg, xo, ang) in enumerate(rows):
        w = measure(txt, size) + 90; h = size * 1.18 + 56
        E.append(El(block(txt, size, fg, bg, ang, padx=45, pady=28, ol=10, sh=16), 62 + 14 + xo + w / 2, y + h / 2, t0 + .07 * i, 2.2, -ang * 4, ph=y, dur=0.26)); y += int(h) + 22
    sv = Sticker(470, 160, CH, ["저장해 두기"], 78, YEL, ol=10, sh=16, angle=-4, shc=OR)
    E.append(El(sv, 62 + 20 + sv.w / 2, 1235, ws(32), 2.2, 14, idle=1.5))
PAY_ARROW_AT = None
hook(); term(); meaning(); example_en(); example_ko(); payoff()

def arrow_sticker():
    w, h, k, ol, sh = 150, 190, 2, 8, 12; pad = ol + sh + 4
    im = Image.new("RGBA", ((w + 2 * pad) * k, (h + 2 * pad) * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def poly(o):
        pts = [(w * .3, 0), (w * .7, 0), (w * .7, h * .5), (w, h * .5), (w / 2, h), (0, h * .5), (w * .3, h * .5)]
        return [((pad + x + (o if x > w / 2 else -o if x < w / 2 else 0)) * k, (pad + y + (o if y >= h * .99 else -o if y <= 0 else 0)) * k) for x, y in pts]
    d.polygon([(x + sh * k, y + sh * k) for x, y in poly(ol)], fill=OR); d.polygon(poly(ol), fill=BLK); d.polygon(poly(0), fill=WH)
    s = Sticker(1, 1, None); s.src = im; s.angle = 0; s._c = {}; return s
ARROW = arrow_sticker()

# ---------- background: flat colour + drifting halftone dots ----------
yy, xx = np.mgrid[0:H + 80, 0:W + 80]
DOTS = (((xx % 40) - 20) ** 2 + ((yy % 40) - 20) ** 2) < 36
def bg_frame(t, col):
    k = int(t * 36) % 40
    m = DOTS[k:k + H, k:k + W]
    dark = tuple(int(v * 0.86) for v in col) if col != CH else (34, 34, 34)
    arr = np.empty((H, W, 3), np.uint8); arr[:] = col; arr[m] = dark
    return Image.fromarray(arr, "RGB")

# ---------- shape morph: prison bars -> room (perspective box) ----------
def ease(u): u = min(1, max(0, u)); return u * u * (3 - 2 * u)
BARS = [((70 + i * 134, -60), (70 + i * 134, H + 60)) for i in range(8)]
def room_lines(sc, cx=540, cy=900):
    hw, hh = 250 * sc, 340 * sc
    TL, TR, BR, BL = (cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)
    OTL, OTR, OBR, OBL = (-80, -80), (W + 80, -80), (W + 80, H + 80), (-80, H + 80)
    return [(OTL, TL), (BL, TL), (BL, OBL), (TL, TR), (BL, BR), (TR, BR), (TR, OTR), (BR, OBR)]
def lerp(a, b, u): return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
T_MORPH = ws(10)
def draw_bars(img, t, bi):
    d = ImageDraw.Draw(img); col = LINE[bi]
    sc = 1 + 0.03 * math.sin(t * 3) + (0.25 * ease((t - ws(11)) / 1.2) if t >= ws(11) else 0)
    room = room_lines(sc)
    shake = 0
    if t < T_MORPH:
        shake = 7 * math.sin(t * 55) * (1.0 if ws(4) <= t < ws(4) + 1.2 else 0.25) * (math.exp(-max(0, t - ws(4)) / 1.5) if t >= ws(4) else 1)
    for i, (a, b) in enumerate(BARS):
        u = ease((t - T_MORPH - i * 0.045) / 0.55) if t >= T_MORPH else 0
        pa = lerp((a[0] + shake * (1 if i % 2 else -1), a[1]), room[i][0], u); pb = lerp((b[0] + shake * (1 if i % 2 else -1), b[1]), room[i][1], u)
        w = 30 if u < .5 else 22
        sh = ((pa[0] + 10, pa[1] + 10), (pb[0] + 10, pb[1] + 10))
        if col == OR:
            d.line([sh[0], sh[1]], fill=BLK, width=w)
        d.line([pa, pb], fill=col, width=w)
        for p in (pa, pb): d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=col)
    # window on the back wall once the room has formed
    if t >= T_MORPH + 0.9:
        a = ease((t - T_MORPH - 0.9) / 0.3); hw = 90 * a * sc
        cx, cy = 540, 700
        for wd, c in ((30, col),):
            d.rectangle((cx - hw, cy - hw, cx + hw, cy + hw), outline=c, width=14)
            d.line((cx - hw, cy, cx + hw, cy), fill=c, width=10); d.line((cx, cy - hw, cx, cy + hw), fill=c, width=10)

# ---------- bird on a chunky platform ----------
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
    if i not in PLATS: PLATS[i] = Sticker(340, 80, PLAT_COL[i], ol=9, sh=14)
    return PLATS[i]
def beat_idx(t): return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
BCX, PLAT_TOP = 680, 1440
def draw_bird(img, t, fi):
    bi = beat_idx(t); dt = t - BT[bi]
    hop = 28 * math.sin(math.pi * dt / 0.36) if dt < 0.36 else 0
    ps = plat(bi).get(); img.paste(ps, (int(BCX - ps.width / 2), PLAT_TOP - 20), ps)
    b = bird_img(float(ENV[fi])); img.paste(b, (int(BCX - b.width / 2), int(PLAT_TOP - b.height + 40 - hop)), b)

# ---------- chrome ----------
PILL = block("NEWS ENGLISH · CNN", 38, CH, YEL, -2, padx=24, pady=8, ol=6, sh=8)
HANDLE = Sticker(700, 70, CH, ["지나쌤영어  @jina.ssam_english"], 38, WH, ol=6, sh=8, fpath=BOLD_F)
def draw_chrome(img):
    img.paste(PILL.get(), (62 - 6, 218), PILL.get())
    h = HANDLE.get(); img.paste(h, (W // 2 - h.width // 2, 1588 - h.height // 2), h)
def shutters(img, t):  # reveal wipe at every beat change after the hook
    for b in BT[1:]:
        dt = t - b
        if 0 <= dt < 0.22:
            p = dt / 0.22; hh = 1920 / 6 * (1 - p); d = ImageDraw.Draw(img)
            for i in range(6):
                cy = 160 + i * 320; d.rectangle((0, cy - hh / 2, W, cy + hh / 2), fill=CH if i % 2 else YEL)
def draw_dots(img, t):  # typing dots
    if BT[1] + .25 <= t < ws(10):
        for i in range(3):
            r = 15 + 5 * max(0, math.sin(t * 9 - i * 1.0)); cx = 190 + i * 62
            ImageDraw.Draw(img).ellipse((cx - r, 600 - r, cx + r, 600 + r), fill=CH)
def starburst(img, t):
    if t < BT[2]: return
    k = 2; S = 880 * k; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = S / 2
    n = 14; ang = math.radians(t * 70)
    def pts(R, r):
        return [(c + (R if i % 2 == 0 else r) * k * math.cos(ang + i * math.pi / n), c + (R if i % 2 == 0 else r) * k * math.sin(ang + i * math.pi / n)) for i in range(2 * n)]
    pu = min(1, (t - BT[2]) / 0.3); R0 = 400 * ease_back(pu)
    d.polygon([(x + 18 * k, y + 18 * k) for x, y in pts(R0, R0 * .78)], fill=OR)
    d.polygon(pts(R0 + 10, R0 * .78 + 10), fill=BLK); d.polygon(pts(R0, R0 * .78), fill=YEL)
    im = im.resize((S // k, S // k), Image.LANCZOS); img.paste(im, (430 - im.width // 2, 900 - im.height // 2), im)
def draw_arrow(img, t):
    if t >= ws(32):
        bounce = abs(math.sin((t - ws(32)) * 7.5)) * 34
        a = ARROW.get(); img.paste(a, (700 - a.width // 2, int(1000 - bounce) - a.height // 2), a)
        # bookmark flag on the save sticker corner
        d = ImageDraw.Draw(img); x, y = 740, 1060
        d.polygon([(x - 8, y - 8), (x + 70, y - 8), (x + 70, y + 100), (x + 31, y + 70), (x - 8, y + 100)], fill=BLK)
        d.polygon([(x, y), (x + 62, y), (x + 62, y + 84), (x + 31, y + 60), (x, y + 84)], fill=WH)

def frame(t, fi):
    bi = beat_idx(t); img = bg_frame(t, BG[bi]); draw_bars(img, t, bi)
    if bi == 2: starburst(img, t)
    for e in ELS[bi]: draw_el(img, e, t)
    if bi == 1: draw_dots(img, t)
    if bi == 5: draw_arrow(img, t)
    shutters(img, t); draw_bird(img, t, fi); draw_chrome(img)
    return img

MARKS = {"hook_0.0": 0.0, "hook_0.2": 0.2, "hook_0.3": 0.3, "hook_1.0": 1.0, "hook_end": 3.8, "term_typing": 4.8, "term_slam": 5.9,
         "term_room": 7.6, "meaning": 10.0, "example_en": 13.8, "example_ko": 16.8, "payoff": 19.2}
def render():
    os.makedirs(FR, exist_ok=True); nfr = int(round(TOTAL * FPS)); out = f"{OUT}/kw_{RID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", MP3, "-filter_complex", "[1:a]apad,aformat=channel_layouts=stereo[a]", "-map", "0:v", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "1", "-c:a", "aac", "-b:a", "192k",
           "-ar", "44100", "-t", f"{TOTAL:.3f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE); mk = {round(v * FPS): k for k, v in MARKS.items()}
    for i in range(nfr):
        im = frame(i / FPS, i); p.stdin.write(im.tobytes())
        if i in mk: im.save(f"{FR}/kw_{RID}_{mk[i]}.png")
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg")
    print("done", out, TOTAL)
def report_contrast():
    pairs = {"charcoal/warm white (hook words, cards)": (CH, WH), "charcoal/orange (term, hl box)": (CH, OR), "charcoal/yellow (labels, hl)": (CH, YEL),
             "warm white/charcoal (labels, ko card)": (WH, CH), "yellow/charcoal (save sticker)": (YEL, CH), "warm white/orange (technically tag)": (WH, OR)}
    for k, (a, b) in pairs.items(): print(f"{contrast(a, b):5.2f}  {k}")
if __name__ == "__main__":
    report_contrast()
    if "--frames" in sys.argv:
        os.makedirs(FR, exist_ok=True)
        for k, v in MARKS.items(): frame(v, int(v * FPS)).save(f"{FR}/kw_{RID}_{k}.png")
    else: render()
