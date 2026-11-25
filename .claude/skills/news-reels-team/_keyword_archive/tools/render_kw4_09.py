#!/usr/bin/env python3
"""kw v4 reel 09 'pay ~ in rent' : restrained LIQUID motion (slow soft blobs + one ripple on the answer).
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw4_09.py [--frames t1,t2,...]
  --frames : only write PNGs to 06_keyword_reels/v4/frames (no video)."""
import os, sys, json, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
RID = "09"; W, H = 1080, 1920; FPS = 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels/v4"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
MP3 = f"{ROOT}/audio/v3/kw_{RID}.mp3"
FD = "/usr/share/fonts/opentype/noto/NotoSansCJK-"
F32 = np.float32
INK = (28, 34, 36); CREAM = (245, 238, 221); CORAL = (228, 136, 110); TEAL = (62, 108, 108); TEALD = (44, 82, 86)

def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

WK = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[RID]
words = WK["words"]; BEATS = WK["beats"]; BT = [b["start"] for b in BEATS]
# Scribe zero-length word guard (min 0.08 s) -- reported if any
ZERO = [w for w in words if w["e"] - w["s"] < 0.08]
AUDIO_DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
TOTAL = AUDIO_DUR + TAIL; NF = int(round(TOTAL * FPS))

def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def ease(p): p = min(1, max(0, p)); return p * p * (3 - 2 * p)
def blurf(M, r): return cv2.GaussianBlur(M, (0, 0), r) if r > 0 else M
_fc = {}
def font(sz, w="Bold"):
    k = (sz, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}{w}.ttc", sz, index=1)
    return _fc[k]

# ------------------------------------------------------------------ background: slow soft blobs (low contrast)
BW_, BH_ = 108, 192
_yy, _xx = np.mgrid[0:BH_, 0:BW_].astype(F32); UU = _xx / BH_ * 2.0; VV = _yy / BH_ * 2.0
_r = np.random.default_rng(7)
BLOBS = [(_r.uniform(.1, .45), _r.uniform(.2, .8), _r.uniform(.12, .3), _r.uniform(.1, .25), _r.uniform(0, 6.3), _r.uniform(0, 6.3), _r.uniform(.16, .30), k % 3) for k in range(8)]
GRAD = np.linspace(0, 1, BH_, dtype=F32)[:, None, None]
def background(t):
    wu = UU + .06 * np.sin(VV * 2.2 + t * .35); wv = VV + .06 * np.sin(UU * 2.6 + t * .3)
    img = np.array(TEALD, F32)[None, None] * (1 - GRAD) + np.array(TEAL, F32)[None, None] * GRAD * .95
    img = np.broadcast_to(img, (BH_, BW_, 3)).copy()
    cols = [(86, 130, 126), (190, 128, 110), (214, 205, 184)]; amps = [.50, .20, .10]
    for ax, ay, fx, fy, px, py, r, k in BLOBS:
        cx = .56 + ax * math.sin(fx * t + px); cy = 1 + ay * 1.3 * math.sin(fy * t + py)
        f = r * r / ((wu - cx) ** 2 + (wv - cy) ** 2 + 2e-3)
        m = sstep(.7, 1.5, f)[..., None] * amps[k]
        img = img * (1 - m) + np.array(cols[k], F32)[None, None] * m
    img = cv2.GaussianBlur(img, (0, 0), 1.0)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC).astype(F32)
_DY, _DX = np.mgrid[0:H, 0:W].astype(F32)
RIP_C = (456, 690); _RD = np.sqrt((_DX - RIP_C[0]) ** 2 + (_DY - RIP_C[1]) ** 2)
def ripples(fr, t, t0):
    p0 = t - t0
    for k in range(3):
        p = p0 - k * .55
        if p < 0 or p > 3.2: continue
        r = 150 + 520 * ease(p / 3.2) ** .8; a = .16 * (1 - p / 3.2) ** 1.5
        ring = np.exp(-((_RD - r) / 16.0) ** 2) * a
        fr += ring[..., None] * (np.array(CREAM, F32)[None, None] - fr) * 1.0

# ------------------------------------------------------------------ text layout
MAXW = 724; CX = 456; PX0, PX1 = 62, 850
class Tok:
    def __init__(s, txt, sz, hl, w0, w1, w="Bold"):
        s.txt, s.sz, s.hl, s.w0, s.w1, s.w = txt, sz, hl, w0, w1, w
        f = font(sz, w); s.len = f.getlength(txt)
def tokens_for(beat, hl_set, sz, w="Bold"):
    """show tokens -> word index spans. a token with digits spans 3 words (eight hundred dollars...)."""
    toks = beat["show"].split(); i = beat["first_word_idx"]; out = []
    for j, t in enumerate(toks):
        n = 3 if any(c.isdigit() for c in t) else 1
        out.append(Tok(t, sz, j in hl_set, i, i + n - 1, w)); i += n
    assert i - beat["first_word_idx"] == beat["n_words"], (beat["role"], i, beat["n_words"])
    return out
def wrap(toks, maxw, gap=.30):
    lines = [[]]; cur = 0
    for t in toks:
        sp = t.sz * gap
        if lines[-1] and cur + sp + t.len > maxw: lines.append([]); cur = 0
        cur += (sp if lines[-1] else 0) + t.len; lines[-1].append(t)
    return lines
class Panel:
    """lines of Tok, centred at CX. top y of panel = y0; builds token placement."""
    def __init__(s, name, lines, y0, kind="cream", lh=1.42, pad_v=44, gap=.30):
        s.name, s.kind, s.y0 = name, kind, y0; s.placed = []; y = y0 + pad_v
        for ln in lines:
            sz = max(t.sz for t in ln); step = int(sz * lh)
            tot = sum(t.len for t in ln) + sum(t.sz * gap for t in ln[1:]); x = CX - tot / 2
            base = y + int(sz * .98)
            for t in ln:
                s.placed.append((t, x, base)); x += t.len + t.sz * gap
            y += step
        s.y1 = y + pad_v - int(max(t.sz for t in lines[-1]) * .42) + 22
        s.rect = (PX0, y0, PX1, s.y1); s.key = (name, tuple((t.txt, t.sz) for t, _, _ in s.placed))
        # text masks
        s.masks = []
        for t, x, base in s.placed:
            f = font(t.sz, t.w); pd = 6
            wd = int(t.len) + 2 * pd; ht = int(t.sz * 1.5)
            im = Image.new("L", (wd, ht), 0); ImageDraw.Draw(im).text((pd, int(t.sz * 1.1)), t.txt, font=f, fill=255, anchor="ls")
            s.masks.append((np.asarray(im, F32) / 255, int(round(x)) - pd, base - int(t.sz * 1.1)))
        # highlight boxes (merge adjacent on the same line)
        s.boxes = []
        for i, (t, x, base) in enumerate(s.placed):
            if not t.hl: continue
            sz = t.sz; x0 = x - sz * .16; x1 = x + t.len + sz * .16
            if i + 1 < len(s.placed) and s.placed[i + 1][0].hl and s.placed[i + 1][2] == base: x1 = s.placed[i + 1][1] - sz * .02
            if i > 0 and s.placed[i - 1][0].hl and s.placed[i - 1][2] == base: x0 = s.placed[i - 1][1] + s.placed[i - 1][0].len + sz * .02
            s.boxes.append((i, x0, base - sz * .86, x1, base + sz * .26))
        s.pmask = None
    def panel_mask(s):
        if s.pmask is None:
            x0, y0, x1, y1 = s.rect; pad = 50; w, h = x1 - x0, y1 - y0; ss = 2
            im = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0)
            ImageDraw.Draw(im).rounded_rectangle((pad * ss, pad * ss, (pad + w) * ss, (pad + h) * ss), radius=58 * ss, fill=255)
            s.pmask = np.asarray(im.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS), F32) / 255
        return s.pmask, 50
_g = {}
def wob(M, t, amp, seed):
    h, w = M.shape
    if (h, w) not in _g: _g[(h, w)] = np.mgrid[0:h, 0:w].astype(F32)
    gy, gx = _g[(h, w)]
    return cv2.remap(M, (gx + amp * np.sin(gy * .02 + t * .9 + seed)).astype(F32), (gy + amp * .8 * np.sin(gx * .024 + t * 1.1 + seed * 2)).astype(F32), cv2.INTER_LINEAR, borderValue=0)
def paste(fr, rgb, a, x, y):
    x = int(round(x)); y = int(round(y)); h, w = a.shape
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    rgb = np.asarray(rgb, F32); r = rgb if rgb.ndim == 1 else rgb[y0 - y:y1 - y, x0 - x:x1 - x]
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - aa) + r * aa
FILL_D = .22
def fill_of(t, w0): return float(sstep(S(w0), S(w0) + FILL_D, t))
def S(i): return words[i]["s"]
def draw_panel(fr, P, t, alpha, dy=0, swell=1.0):
    if alpha < .01: return
    pm, pad = P.panel_mask(); x0, y0, x1, y1 = P.rect
    M = wob(pm, t, 2.2, hash(P.name) % 7)
    if swell != 1.0:
        h, w = M.shape; A = np.array([[swell, 0, w / 2 * (1 - swell)], [0, swell, h / 2 * (1 - swell)]], F32); M = cv2.warpAffine(M, A, (w, h))
    X, Y = x0 - pad, y0 - pad + dy
    sh = blurf(np.roll(M, 16, 0), 16) * .30 * alpha
    paste(fr, np.array((10, 24, 26), F32), sh, X, Y)
    base = np.array(CREAM if P.kind == "cream" else CORAL, F32)
    # faint top sheen for a glassy feel
    gy = np.linspace(1.04, .965, M.shape[0], dtype=F32)[:, None, None]
    paste(fr, np.clip(base[None, None] * gy, 0, 255), M * .94 * alpha, X, Y)
    ink = np.array(INK, F32); hlc = np.array(CORAL if P.kind == "cream" else CREAM, F32)
    # highlight boxes
    for i, bx0, by0, bx1, by1 in P.boxes:
        f = fill_of(t, P.placed[i][0].w0)
        a = (.22 + .78 * f) * alpha if P.kind == "cream" else 0
        if a < .01: continue
        w_, h_ = int(bx1 - bx0), int(by1 - by0)
        im = np.zeros((h_ + 20, w_ + 20), F32); cv2.rectangle(im, (10 + h_ // 2, 10), (10 + w_ - h_ // 2, 10 + h_), 1.0, -1); cv2.circle(im, (10 + h_ // 2, 10 + h_ // 2), h_ // 2, 1.0, -1, cv2.LINE_AA); cv2.circle(im, (10 + w_ - h_ // 2, 10 + h_ // 2), h_ // 2, 1.0, -1, cv2.LINE_AA)
        im = blurf(im, 1.0)
        paste(fr, np.array(CORAL, F32), im * a * (.75 + .25 * f), bx0 - 10, by0 - 10 + dy)
    for (t_, x, base), (m, mx, my) in zip(P.placed, P.masks):
        f = fill_of(t, t_.w0); a = (.36 + .64 * f) * alpha
        paste(fr, ink, m * a, mx, my + dy)

# ------------------------------------------------------------------ beats -> panel sets
B = {b["role"]: b for b in BEATS}
def single(role, sz, hl=(), kind="cream", y0=None, w="Bold"):
    toks = tokens_for(B[role], set(hl), sz, w); lines = wrap(toks, MAXW)
    P = Panel("main", lines, 0, kind); h = P.y1; top = 270 if y0 is None else y0
    cy = 690; top = int(cy - h / 2) if y0 is None else y0
    return Panel("main", lines, top, kind)
def answer_panel():
    b = B["answer"]; i = b["first_word_idx"]
    def build(sz):
        mk = lambda txt, wi: Tok(txt, sz, False, wi, wi, "Black")
        return [mk("pay", i + 1), mk("~", i + 2)], [mk("in", i + 3), mk("rent", i + 4)]
    sz = 196
    while True:
        l1, l2 = build(sz)
        if max(sum(t.len for t in l) + sz * .30 for l in (l1, l2)) <= MAXW - 20: break
        sz -= 6
    lab = [Tok("정답은…", 62, False, i, i, "Bold")]
    h = Panel("main", [lab, l1, l2], 0, "coral", lh=1.2, pad_v=50).y1
    return Panel("main", [lab, l1, l2], int(690 - h / 2) - 10, "coral", lh=1.2, pad_v=50)
def ex_panels(en_role, ko_role, en_hl, ko_hl):
    pe = Panel("en", wrap(tokens_for(B[en_role], set(en_hl), 66), MAXW), 262, "cream", lh=1.40, pad_v=38)
    # en panel is always fully shown once its beat has started (ko beat: words already spoken)
    out = [pe]
    if ko_role:
        out.append(Panel("ko", wrap(tokens_for(B[ko_role], set(ko_hl), 66), MAXW), pe.y1 + 34, "cream", lh=1.40, pad_v=38))
    return out
def tok_idx(role, txt):
    b = B[role]; return [j for j, t in enumerate(b["show"].split()) if t == txt]
STATES = [
    [single("hook", 82, hl=[6])],
    [single("question", 76)],
    [answer_panel()],
    [single("meaning", 80, hl=[0, 1, 2])],
    ex_panels("ex1_en", None, [1, 6, 7], []),
    ex_panels("ex1_en", "ex1_ko", [1, 6, 7], [1, 4]),
    ex_panels("ex2_en", None, [4, 5, 6], []),
    ex_panels("ex2_en", "ex2_ko", [4, 5, 6], [1, 2]),
]
# make sure the highlighted en tokens are the expression ones
for role, st in (("ex1_en", STATES[4]), ("ex2_en", STATES[6])):
    print(role, [t.txt for t, _, _ in st[0].placed if t.hl])
for role, st in (("hook", STATES[0]), ("meaning", STATES[3])):
    print(role, [t.txt for t, _, _ in st[0].placed if t.hl])
print("ko hl", [t.txt for t, _, _ in STATES[5][1].placed if t.hl], [t.txt for t, _, _ in STATES[7][1].placed if t.hl])
BEAT_STATE = [0, 1, 2, 3, 4, 5, 6, 7]  # beat index -> state index

# ------------------------------------------------------------------ key image: house + calendar, coin dropping into a slot
KX0, KY0, KW_, KH_ = 62, 1168, 500, 272
SS = 2
def build_key():
    w, h = KW_ * SS, KH_ * SS
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=50 * SS, fill=CREAM + (222,))
    s = SS
    # house (left)
    hx, hy = 40, 110
    d.polygon([((hx - 8) * s, (hy + 58) * s), ((hx + 62) * s, (hy - 6) * s), ((hx + 132) * s, (hy + 58) * s)], fill=CORAL + (255,))
    d.rectangle(((hx + 8) * s, (hy + 56) * s, (hx + 116) * s, (hy + 140) * s), fill=(236, 222, 196, 255))
    d.rounded_rectangle(((hx + 46) * s, (hy + 88) * s, (hx + 78) * s, (hy + 140) * s), radius=8 * s, fill=TEAL + (255,))
    d.ellipse(((hx + 68) * s, (hy + 112) * s, (hx + 73) * s, (hy + 117) * s), fill=CREAM + (255,))
    d.rectangle(((hx + 18) * s, (hy + 72) * s, (hx + 40) * s, (hy + 94) * s), fill=TEAL + (255,))
    d.rectangle(((hx + 86) * s, (hy + 72) * s, (hx + 108) * s, (hy + 94) * s), fill=TEAL + (255,))
    d.line((16 * s, (hy + 141) * s, 170 * s, (hy + 141) * s), fill=TEALD + (255,), width=3 * s)
    # calendar (right)
    cx0, cy0, cx1, cy1 = 250, 36, 470, 244
    d.rounded_rectangle((cx0 * s, cy0 * s, cx1 * s, cy1 * s), radius=18 * s, fill=(252, 249, 240, 255), outline=TEALD + (255,), width=3 * s)
    d.rounded_rectangle((cx0 * s, cy0 * s, cx1 * s, (cy0 + 44) * s), radius=18 * s, fill=TEAL + (255,))
    d.rectangle((cx0 * s, (cy0 + 28) * s, cx1 * s, (cy0 + 44) * s), fill=TEAL + (255,))
    for rx in (cx0 + 40, cx1 - 40): d.rounded_rectangle(((rx - 5) * s, (cy0 - 10) * s, (rx + 5) * s, (cy0 + 14) * s), radius=5 * s, fill=TEALD + (255,))
    gx0, gy0 = cx0 + 15, cy0 + 60; cw, ch = 46, 34
    for r in range(4):
        for c in range(4):
            x = gx0 + c * (cw + 3); y = gy0 + r * (ch + 3)
            hot = (r == 1 and c == 2)
            d.rounded_rectangle((x * s, y * s, (x + cw - 4) * s, (y + ch - 4) * s), radius=6 * s, fill=(CORAL + (255,)) if hot else (226, 220, 204, 255))
    return im.resize((KW_, KH_), Image.LANCZOS)
KEY = build_key()
SLOT = (250 + 15 + 2 * 49 + 21, 36 + 60 + 37 + 14)    # centre of the hot cell (local coords): slot slit location
DOOR = (40 + 62, 110 + 120)
def key_layer(t):
    im = KEY.copy(); d = ImageDraw.Draw(im, "RGBA")
    # slot slit on the hot cell
    sx, sy = SLOT; d.rounded_rectangle((sx - 15, sy - 3, sx + 15, sy + 3), radius=3, fill=INK + (255,))
    # coin: leaves the door, arcs over, drops into the slit (loop 3.0 s, with 0.5 s rest)
    p = (t % 3.2) / 2.6
    if p < 1:
        e = ease(p); x0, y0 = DOOR[0] + 6, DOOR[1] - 4
        x = x0 + (sx - x0) * e; y = y0 + (sy - y0) * e - 150 * math.sin(math.pi * e) ** 1.2 * (1 - .15 * e)
        sq = abs(math.cos(p * 7.0)) * .75 + .25; r = 20
        if y < sy - 1:
            coin = Image.new("RGBA", (80, 80), (0, 0, 0, 0)); dc = ImageDraw.Draw(coin)
            dc.ellipse((40 - r * sq, 40 - r, 40 + r * sq, 40 + r), fill=(238, 190, 112, 255), outline=(190, 120, 80, 255), width=3)
            if sq > .45: dc.ellipse((40 - r * sq * .5, 40 - r * .5, 40 + r * sq * .5, 40 + r * .5), outline=(190, 120, 80, 255), width=2)
            cl = Image.new("RGBA", im.size, (0, 0, 0, 0)); cl.paste(coin, (int(x - 40), int(y - 40)))
            ca = np.array(cl); ca[int(sy - 1):, :, 3] = 0
            im = Image.alpha_composite(im, Image.fromarray(ca))
    return im
def draw_key(fr, t, alpha=1.0):
    im = key_layer(t); a = np.asarray(im, F32) / 255
    sh = blurf(np.pad(np.roll(a[..., 3], 12, 0), 30), 12) * .25
    paste(fr, np.array((10, 24, 26), F32), sh, KX0 - 30, KY0 - 30)
    paste(fr, a[..., :3] * 255, a[..., 3] * alpha, KX0, KY0)

# ------------------------------------------------------------------ bird + handle
BENV = bird.envelope(MP3, FPS, NF)
def draw_bird(fr, i, t):
    bob = 5 * math.sin(t * 1.8)
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
    bird.place(img, float(BENV[min(i, len(BENV) - 1)]), 724, int(1440 + bob))
    return np.asarray(img.convert("RGB"), F32)
_hf = font(34, "Bold"); HTXT = "지나쌤영어  @jina.ssam_english"
_hm = Image.new("L", (int(_hf.getlength(HTXT)) + 40, 70), 0); ImageDraw.Draw(_hm).text((20, 48), HTXT, font=_hf, fill=255, anchor="ls"); HM = np.asarray(_hm, F32) / 255
def draw_handle(fr):
    h, w = HM.shape; x = W / 2 - w / 2; y = 1588 - h / 2
    paste(fr, np.array((20, 40, 42), F32), np.clip(blurf(HM, 9) * 2.5, 0, .55), x, y)
    paste(fr, np.array(CREAM, F32), HM, x, y)

# ------------------------------------------------------------------ frame assembly
def beat_idx(t): return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
TR = .40
def render(i):
    t = i / FPS; bi = beat_idx(t); fr = background(t)
    if bi >= 2 and t - BT[2] < 3.4: ripples(fr, t, BT[2])
    draw_key(fr, t)
    st = STATES[BEAT_STATE[bi]]; p = (t - BT[bi]) / TR if bi > 0 else 1.0; pa = ease(p)
    old = STATES[BEAT_STATE[bi - 1]] if bi > 0 and p < 1 else []
    newkeys = {P.key for P in st}
    for P in old:
        if P.key in newkeys: continue
        draw_panel(fr, P, t, 1 - pa, dy=-10 * pa)
    for P in st:
        same = any(o.key == P.key for o in old)
        sw = 1.0
        if P.kind == "coral": sw = .965 + .035 * ease((t - BT[bi]) / 1.4)
        draw_panel(fr, P, t, 1.0 if same else pa, dy=0 if same else 14 * (1 - pa), swell=sw)
    fr = draw_bird(fr, i, t)
    draw_handle(fr)
    return np.clip(fr, 0, 255).astype(np.uint8)

def checks():
    for n, a, b in [("ink / cream panel", INK, CREAM), ("ink / coral highlight", INK, CORAL), ("ink / coral panel", INK, CORAL),
                    ("ink / cream-coral blend worst", INK, (245, 238, 221)), ("handle cream / teal-dark bg", CREAM, (50, 90, 92)),
                    ("handle cream / teal bg + lightest blob", CREAM, (92, 132, 126))]:
        print(f"contrast {n}: {contrast(a, b):.2f}")
    print("zero/short words:", [(w['t'], w['s'], w['e']) for w in ZERO])
    for st in STATES:
        for P in st: print(P.name, P.rect, [round(x[1]) for x in P.placed][:3], "max x", max(x + t.len for t, x, _ in P.placed), "min x", min(x for _, x, _ in P.placed))

if __name__ == "__main__":
    checks()
    if "--frames" in sys.argv:
        for ts in sys.argv[sys.argv.index("--frames") + 1].split(","):
            Image.fromarray(render(int(round(float(ts) * FPS)))).save(f"{FR}/kw_{RID}_t{ts}.png")
        sys.exit()
    outp = f"{OUT}/kw_{RID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", MP3,
           "-map", "0:v", "-map", "1:a", "-af", "apad", "-t", f"{TOTAL:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-threads", "2", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", outp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(NF):
        p.stdin.write(render(i).tobytes())
        if i % 60 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait(); print("done", outp)
