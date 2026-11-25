#!/usr/bin/env python3
"""kw 2026-11-25 reel 09 'pay ~ in rent' : LIQUID MOTION + KINETIC TYPOGRAPHY (숫자형 hook).
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw_1125_09.py [--frames t1,t2,...]
  --frames : only write PNGs to 06_keyword_reels/frames (no video)."""
import os, sys, json, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
RID = "09"; W, H = 1080, 1920; FPS = 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
MP3 = f"{ROOT}/audio/kw_{RID}.mp3"
FD = "/usr/share/fonts/opentype/noto/NotoSansCJK-"
F32 = np.float32
CH = (18, 18, 18); WW = (253, 249, 234); OR = (254, 81, 5); DEEP = (70, 22, 3); SLABC = (24, 22, 22)

def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

SPEC = json.load(open(f"{ROOT}/03_script/keyword_scripts.json"))["reels"]
SPEC = next(r for r in SPEC if str(r["id"]) == RID) if isinstance(SPEC, list) else SPEC[RID]
WK = json.load(open(f"{ROOT}/audio/words_kw.json"))[RID]
words = WK["words"]; BEATS = WK["beats"]; BT = [b["start"] for b in BEATS]
assert [b["role"] for b in BEATS] == [b["role"] for b in SPEC["beats"]]
AUDIO_DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
TOTAL = AUDIO_DUR + TAIL; NF = int(round(TOTAL * FPS))
def S(i): return words[i]["s"]

# ------------------------------------------------------------------ small math / image helpers
_fc = {}
def font(sz, w="Black"):
    k = (sz, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}{w}.ttc", sz, index=1)
    return _fc[k]
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def blurf(M, r): return cv2.GaussianBlur(M, (0, 0), r) if r > 0 else M
def goo(M, r, th=.5, soft=.12): return sstep(th - soft, th + soft, blurf(M, r)).astype(F32)
def eo3(p): p = min(1, max(0, p)); return 1 - (1 - p) ** 3
def back(p):
    p = min(1, max(0, p)); c = 1.70158; q = p - 1; return 1 + (c + 1) * q ** 3 + c * q ** 2
_grid = {}
def wob(M, t, amp, seed=0., fx=.02, sp=2.0):
    h, w = M.shape
    if (h, w) not in _grid: _grid[(h, w)] = np.mgrid[0:h, 0:w].astype(F32)
    gy, gx = _grid[(h, w)]
    mx = gx + amp * np.sin(gy * fx + t * sp + seed); my = gy + amp * .8 * np.sin(gx * fx * 1.2 + t * sp * 1.3 + seed * 2)
    return cv2.remap(M, mx.astype(F32), my.astype(F32), cv2.INTER_LINEAR, borderValue=0)
def shade(M, col, r, spec=.8, pw=26, amb=.62, dif=.55):
    h = blurf(M, r); gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8
    k = r * 2.4; nx = -gx * k; ny = -gy * k; nrm = np.sqrt(nx * nx + ny * ny + 1)
    L = np.array((-.45, -.6, .66)); L /= np.linalg.norm(L); Hh = L + np.array((0, 0, 1)); Hh /= np.linalg.norm(Hh)
    d = np.clip((nx * L[0] + ny * L[1] + L[2]) / nrm, 0, 1); s = np.clip((nx * Hh[0] + ny * Hh[1] + Hh[2]) / nrm, 0, 1) ** pw
    c = np.array(col, F32)[None, None]
    rgb = c * (amb + dif * d)[..., None] + 255 * spec * s[..., None] * np.array((1, .97, .9), F32)
    return np.clip(rgb, 0, 255)
def paste(fr, rgb, a, x, y):
    x = int(round(x)); y = int(round(y)); h, w = a.shape
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    rgb = np.asarray(rgb, F32)
    r = rgb if rgb.ndim == 1 else rgb[y0 - y:y1 - y, x0 - x:x1 - x]
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - aa) + r * aa
def draw_layer(fr, M, x, y, col, r=4, shadow=.5, sh_off=(0, 10), sh_r=9, spec=.8, alpha=1.0):
    if M.max() < .01: return
    if shadow:
        Sh = blurf(np.roll(M, (sh_off[1], sh_off[0]), (0, 1)), sh_r) * shadow * alpha
        paste(fr, np.array((8, 8, 8), F32), Sh, x, y)
    paste(fr, shade(M, col, r, spec), M * alpha, x, y)

# ------------------------------------------------------------------ text masks
P = 30; _tm = {}
def tmask(txt, sz, w="Black"):
    k = (txt, sz, w)
    if k not in _tm:
        f = font(sz, w); wd = int(f.getlength(txt)) + 2 * P; ht = int(sz * 1.75); base = int(sz * 1.2)
        im = Image.new("L", (wd, ht), 0); ImageDraw.Draw(im).text((P, base), txt, font=f, fill=255, anchor="ls")
        _tm[k] = (np.asarray(im, F32) / 255, base)
    return _tm[k]
def tlen(txt, sz, w="Black"): return font(sz, w).getlength(txt)
_pm = {}
def rrect_mask(w, h, rad, pad=40):
    k = (w, h, rad, pad)
    if k not in _pm:
        ss = 2; im = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0)
        ImageDraw.Draw(im).rounded_rectangle((pad * ss, pad * ss, (pad + w) * ss, (pad + h) * ss), radius=rad * ss, fill=255)
        _pm[k] = np.asarray(im.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS), F32) / 255
    return _pm[k]
def place(canvas, m, x, y):
    """max-compose mask m with top-left (x,y) into canvas, clipped."""
    h, w = m.shape; H0, W0 = canvas.shape; x = int(round(x)); y = int(round(y))
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W0, x + w), min(H0, y + h)
    if x1 <= x0 or y1 <= y0: return
    np.maximum(canvas[y0:y1, x0:x1], m[y0 - y:y1 - y, x0 - x:x1 - x], out=canvas[y0:y1, x0:x1])
def xform(m, pivx, pivy, sx, sy, X, Y, shape, dx=0, dy=0):
    """scale mask m about local pivot, top-left at (X,Y) in canvas, extra offset."""
    A = np.array([[sx, 0, X + pivx - sx * pivx + dx], [0, sy, Y + pivy - sy * pivy + dy]], F32)
    return cv2.warpAffine(m, A, (shape[1], shape[0]), flags=cv2.INTER_LINEAR, borderValue=0)

# ------------------------------------------------------------------ liquid background (domain-warped metaballs, lowres)
BW_, BH_ = 216, 384
_yy, _xx = np.mgrid[0:BH_, 0:BW_].astype(F32); UU = _xx / BH_ * 2.0; VV = _yy / BH_ * 2.0   # x in 0..1.125, y in 0..2
_r = np.random.default_rng(25)
BLOBS = [(_r.uniform(.15, .5), _r.uniform(.2, .85), _r.uniform(.25, .7), _r.uniform(.2, .6), _r.uniform(0, 6.3), _r.uniform(0, 6.3), _r.uniform(.15, .30)) for _ in range(9)]
def background(t):
    wu = UU + .10 * np.sin(VV * 2.6 + t * .9) + .05 * np.sin(VV * 5.1 - t * 1.3)
    wv = VV + .10 * np.sin(UU * 3.1 + t * .7) + .05 * np.sin(UU * 6.3 + t * 1.1)
    f = np.zeros_like(UU)
    for ax, ay, fx, fy, px, py, r in BLOBS:
        cx = .56 + ax * math.sin(fx * t + px); cy = 1 + ay * 1.3 * math.sin(fy * t + py)
        f += r * r / ((wu - cx) ** 2 + (wv - cy) ** 2 + 2e-3)
    lf = np.log(f + 1e-4); gx = cv2.GaussianBlur(np.gradient(lf, axis=1), (0, 0), 1.2); gy = cv2.GaussianBlur(np.gradient(lf, axis=0), (0, 0), 1.2)
    nx, ny = -gx * 3.0, -gy * 3.0; nrm = np.sqrt(nx * nx + ny * ny + 1)
    L = np.array((-.45, -.6, .66)); L /= np.linalg.norm(L); Hh = L + np.array((0, 0, 1)); Hh /= np.linalg.norm(Hh)
    sp = np.clip((nx * Hh[0] + ny * Hh[1] + Hh[2]) / nrm, 0, 1) ** 40
    ins = sstep(.92, 1.12, f); depth = sstep(1.0, 2.6, f)
    blob = np.array(OR, F32)[None, None] * (1 - depth[..., None]) + np.array(DEEP, F32)[None, None] * depth[..., None]
    halo = (np.clip(f, 0, 1) ** 3 * .30)[..., None] * np.array((150, 50, 8), F32)[None, None]
    base = np.array((20, 18, 18), F32)[None, None] + halo + 5 * np.sin(VV * 9 + UU * 4 + t * .6)[..., None]
    img = base * (1 - ins[..., None]) + blob * ins[..., None]
    img += 255 * (sp * ins * (1 - sstep(1.7, 3.2, f)) * .85)[..., None] * np.array((1, .96, .88), F32)
    img = np.clip(img, 0, 255).astype(np.uint8)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC).astype(F32)

# ------------------------------------------------------------------ liquid slab (rounded panel with orange rim)
def slab(fr, x0, y0, x1, y1, t, seed=0., rad=80, col=SLABC, a=.94, drips=None, orange=False):
    pad = 60; w = x1 - x0; h = y1 - y0
    M = np.zeros((h + 2 * pad + 160, w + 2 * pad), F32); M[:h + 2 * pad, :] = rrect_mask(w, h, rad, pad)
    if drips: M = add_drips(M, t, drips[0], seed, drips[1], 2.6, 15)
    M = goo(wob(M, t, 5, seed, .018, 1.6), 6)
    if orange:
        paste(fr, np.array((8, 8, 8), F32), blurf(np.roll(M, 14, 0), 14) * .6, x0 - pad, y0 - pad)
        paste(fr, shade(M, OR, 16, .55, 30), M, x0 - pad, y0 - pad); return M
    ring = M * (1 - sstep(.62, .92, blurf(M, 8)))
    rgb = shade(M, col, 16, .30, 30, amb=.85, dif=.25)
    rgb = rgb * (1 - ring[..., None]) + np.array(OR, F32)[None, None] * ring[..., None]
    paste(fr, np.array((8, 8, 8), F32), blurf(np.roll(M, 14, 0), 14) * .55, x0 - pad, y0 - pad)
    paste(fr, rgb, M * a, x0 - pad, y0 - pad); return M

def add_drips(M, t, fracs, seed, maxlen, period, w):
    M = M.copy(); cols = np.nonzero(M.max(0) > .6)[0]
    if len(cols) == 0: return M
    c0, c1 = cols.min(), cols.max()
    for j, fr in enumerate(fracs):
        x = int(c0 + fr * (c1 - c0)); found = None
        for dx in range(0, 60):
            for xx in (x + dx, x - dx):
                if 0 <= xx < M.shape[1] and M[:, xx].max() > .6: found = xx; break
            if found is not None: break
        if found is None: continue
        x = found; b = int(np.nonzero(M[:, x] > .6)[0].max()); ph = (t / period + j * .37 + seed * .13 + fr) % 1
        g = min(ph / .72, 1); L = maxlen * g ** 1.5; wd = max(4, int(w * (1 - .3 * g)))
        if ph <= .72:
            cv2.line(M, (x, b - 4), (x, int(b + L)), 1.0, wd, cv2.LINE_AA); cv2.circle(M, (x, int(b + L)), int(wd * .85), 1.0, -1, cv2.LINE_AA)
        else:
            fl = (ph - .72) / .28
            cv2.line(M, (x, b - 4), (x, int(b + L * (1 - fl))), 1.0, max(3, int(wd * (1 - fl * .6))), cv2.LINE_AA)
            yy = int(b + L + fl * fl * 130); cv2.ellipse(M, (x, yy), (int(wd * .7), int(wd * .95)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    return M

# ------------------------------------------------------------------ text items (kinetic words)
class Wd:
    def __init__(s, txt, sz, x, yb, idx, grp, w="Black", enter=None):
        s.txt, s.sz, s.x, s.yb, s.idx, s.grp, s.w, s.enter = txt, sz, x, yb, idx, grp, w, enter
        s.m, s.base = tmask(txt, sz, w); s.t0 = S(idx)
def line_words(toks, sz, yb, cx, idx0, grp_fn, enter_fn=None, w="Black", gap=.28):
    lens = [tlen(t, sz, w) for t in toks]; sp = sz * gap; tot = sum(lens) + sp * (len(toks) - 1); x = cx - tot / 2; out = []
    for i, (t, l) in enumerate(zip(toks, lens)):
        out.append(Wd(t, sz, x, yb, idx0 + i, grp_fn(i, t), w, enter_fn(i) if enter_fn else None)); x += l + sp
    return out
def fit_sz(lines, maxw, hi, lo=40, w="Black", gap=.28):
    for sz in range(hi, lo, -2):
        if max(sum(tlen(t, sz, w) for t in l) + sz * gap * (len(l) - 1) for l in lines) <= maxw: return sz
    return lo

def compose(shape, items, t, ox, oy, ghost=.24, pop=True, amp_wob=2.2):
    """returns ({grp: mask}, ghost_mask_by_grp). items placed at abs coords minus (ox, oy) region origin."""
    act = {}; gh = {}
    for it in items:
        a = act.setdefault(it.grp, np.zeros(shape, F32)); g = gh.setdefault(it.grp, np.zeros(shape, F32))
        X = it.x - P - ox; Y = it.yb - it.base - oy
        p = t - it.t0
        place(g, it.m, X, Y)
        if p < 0: continue
        if it.enter:
            dx0, dy0 = it.enter; q = p / .6; e = eo3(q); rb = (1 - e) * 28
            m = it.m
            if q < 1:
                m = blurf(m, rb) * (1 + rb * .06); m = np.clip(m, 0, 1)
                A = np.array([[1, 0, X + dx0 * (1 - e) ** 2], [0, 1, Y + dy0 * (1 - e) ** 2]], F32)
                a += cv2.warpAffine(m, A, (shape[1], shape[0]), borderValue=0); np.clip(a, 0, 1, out=a)
            else: place(a, m, X, Y)
        elif pop and p < .55:
            sc = 1 + .55 * math.exp(-p * 7) * math.cos(p * 13)
            m = xform(it.m, it.m.shape[1] / 2, it.base * .78, sc, sc, X, Y, shape, 0, -10 * math.exp(-p * 8))
            np.maximum(a, m * min(1, p * 14), out=a)
        else: place(a, it.m, X, Y)
    return act, gh
def draw_groups(fr, shape, ox, oy, act, gh, cols, t, r=4, ghost=.24, wob_amp=2.0, seed=0., shadow=.5, ghost_cols=None):
    for grp, col in cols.items():
        g = gh.get(grp)
        if g is not None and ghost > 0:
            gc = (ghost_cols or cols)[grp]; paste(fr, np.array(gc, F32), goo(g, 2) * ghost, ox, oy)
        a = act.get(grp)
        if a is not None and a.max() > .01:
            a = goo(a, 3, .5, .2)
            if wob_amp: a = wob(a, t, wob_amp, seed + len(grp), .03, 2.2)
            draw_layer(fr, a, ox, oy, col, r=r, shadow=shadow, spec=.7)

# ------------------------------------------------------------------ bird on a liquid blob + header + handle
BENV = bird.envelope(MP3, FPS, NF)
def draw_bird(fr, i, t):
    cx = 690; bob = 7 * math.sin(t * 2.0); by = 1420
    w_, h_ = 460, 240; M = np.zeros((h_, w_), F32); ccx, ccy = w_ // 2, 150
    cv2.ellipse(M, (ccx, ccy + int(3 * math.sin(t * 2.6))), (int(165 + 10 * math.sin(t * 1.9)), int(40 + 5 * math.sin(t * 2.4))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    for k in range(4):
        ang = t * (1.2 + .3 * k) + k * 1.7; bx = ccx + 130 * math.sin(ang); byy = ccy - 12 - 24 * (math.cos(ang * 1.3) * .5 + .5)
        cv2.circle(M, (int(bx), int(byy)), 20 + 5 * k % 3, 1.0, -1, cv2.LINE_AA)
    M = goo(M, 9, .45, .15); M = add_drips(M, t, (.25, .6, .85), 5, 40, 2.2, 11); M = goo(M, 3)
    draw_layer(fr, M, cx - w_ // 2, by - ccy - 20 + int(bob * .4), OR, r=9, shadow=.5, spec=.85)
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
    bird.place(img, float(BENV[min(i, len(BENV) - 1)]), cx, int(by - 18 + bob))
    return np.asarray(img.convert("RGB"), F32)
def make_header():
    pm = rrect_mask(480, 64, 32, 30); ink, _ = tmask("NEWS ENGLISH · CNN", 31, "Black")
    return pm, ink
HDR_PM, HDR_INK = make_header()
def draw_header(fr, t):
    pm = goo(wob(HDR_PM, t, 1.5, 0, .05, 2), 2); y = 224 + 2 * math.sin(t * 2)
    draw_layer(fr, pm, 456 - pm.shape[1] / 2, y, OR, r=7, shadow=.5, spec=.7)
    h, w = HDR_INK.shape; paste(fr, np.array(CH, F32), HDR_INK, 456 - w / 2, y + 62 // 2 + 30 - h / 2 + 6)
HANDLE_M, _hb = tmask("지나쌤영어  @jina.ssam_english", 34, "Bold")
def draw_handle(fr):
    h, w = HANDLE_M.shape; x = W / 2 - w / 2; y = 1588 - h / 2 + 8
    paste(fr, np.array((10, 10, 10), F32), np.clip(blurf(HANDLE_M, 9) * 3, 0, .85), x, y)
    paste(fr, np.array(WW, F32), HANDLE_M, x, y)

# ------------------------------------------------------------------ beat scenes
B = {b["role"]: b for b in BEATS}
def tok_idx(role, n=None): return B[role]["first_word_idx"]

# ---- hook
NUM_SZ = 330
_f = font(NUM_SZ); NUM_ADV = {c: _f.getlength(c) for c in "$0123456789"}
while NUM_ADV["$"] + 3 * max(NUM_ADV[c] for c in "0123456789") > 790:
    NUM_SZ -= 6; _f = font(NUM_SZ); NUM_ADV = {c: _f.getlength(c) for c in "$0123456789"}
CELLW = max(NUM_ADV[c] for c in "0123456789")
NUM_TOT = NUM_ADV["$"] + 3 * CELLW
NREG = (36, 290, 840, int(NUM_SZ * 1.75))     # x, y, w, h
NUM_YB = NREG[1] + int(NUM_SZ * 1.2)          # baseline in abs coords
HK = [("파리", 1), ("초소형", 2), ("방의", 3), ("한", 4), ("달", 5), ("월세예요.", 6)]
HK_SZ = 84
HK_ITEMS = (line_words([w for w, _ in HK[:3]], HK_SZ, 930, 456, 1, lambda i, t: "w") +
            line_words([w for w, _ in HK[3:]], HK_SZ, 1050, 456, 4, lambda i, t: "o" if i == 2 else "w"))
CHIP_TXT, _cb = tmask("달러", 56); CHIP_PM = rrect_mask(190, 84, 42, 30)
def scene_hook(fr, t):
    NW, NH = NREG[2], NREG[3]; x0 = (NW - NUM_TOT) / 2
    xs = [x0, x0 + NUM_ADV["$"]]; xs += [xs[-1] + CELLW * k for k in range(1, 3)]
    chars = ["$"] + list(str(int(round(800 * eo3(t / .8)))).rjust(3, " ")[-3:])
    # ghost full number (visible frame 0)
    G = np.zeros((NH, NW), F32); ow = ["$", "8", "0", "0"]
    for k, c in enumerate(ow):
        m, base = tmask(c, NUM_SZ); cell = NUM_ADV[c] if k == 0 else CELLW
        place(G, m, xs[k] + (cell - NUM_ADV[c]) / 2 - P, NUM_YB - NREG[1] - base)
    A = np.zeros((NH, NW), F32)
    slam = 1 + .30 * math.exp(-t * 8) * math.cos(t * 24)
    for k, c in enumerate(chars):
        if c == " ": continue
        m, base = tmask(c, NUM_SZ); cell = NUM_ADV[c] if k == 0 else CELLW
        X = xs[k] + (cell - NUM_ADV[c]) / 2 - P; Y = NUM_YB - NREG[1] - base
        if t < .8: sy = 1 + .10 * math.sin(t * 38 + k * 2.1)
        else: sy = 1 + .09 * math.sin(t * 5.2 + k * 1.3) * (1 if t > .8 else 0)
        sx = 1 / math.sqrt(sy); sy *= slam; sx *= slam
        pivx = m.shape[1] / 2; pivy = base
        np.maximum(A, xform(m, pivx, pivy, sx, sy, X, Y, A.shape), out=A)
    A = goo(A, 4, .5, .15); A = wob(A, t, 5, 0., .012, 2.0)
    paste(fr, np.array((8, 8, 8), F32), blurf(np.roll(A, 18, 0), 22) * .7, NREG[0], NREG[1])
    if t < .9: paste(fr, np.array(WW, F32), goo(G, 2) * .20 * (1 - sstep(.6, .9, t)), NREG[0], NREG[1])
    ring = sstep(.10, .28, blurf(A, 10)); draw_layer(fr, ring, NREG[0], NREG[1], OR, r=10, shadow=0, spec=.6)
    paste(fr, shade(A, WW, NUM_SZ * .055, .95, 30, amb=.80, dif=.35), A, NREG[0], NREG[1])
    # sentence slab
    slab(fr, 40, 700, 872, 1110, t, 1.0, 78)
    SX, SY = 40, 690
    act, gh = compose((430, 840), HK_ITEMS, t, SX, SY)
    draw_groups(fr, (430, 840), SX, SY, act, gh, {"w": WW, "o": OR}, t, r=3, seed=2)
    # chip "달러" (spoken with the number)
    cs = .5; p = t - cs; sc = 1 + .5 * math.exp(-max(p, 0) * 7) * math.cos(max(p, 0) * 13) if p > 0 else 1
    pm = xform(CHIP_PM, CHIP_PM.shape[1] / 2, CHIP_PM.shape[0] / 2, sc, sc, 0, 0, CHIP_PM.shape)
    pm = goo(wob(pm, t, 1.5, 3, .05, 2), 2)
    if p < 0: paste(fr, np.array(OR, F32), pm * .28, 62 - 30 + 0, 722 - 30 + 0)
    else:
        draw_layer(fr, pm, 62 - 30, 722 - 30, OR, r=8, shadow=.4, spec=.8)
        h, w = CHIP_TXT.shape; paste(fr, np.array(CH, F32), CHIP_TXT * min(1, p * 10), 157 - w / 2, 764 - h / 2 + 4)

# ---- term
TERM_TOK = [("pay", 4), ("~", 5), ("in", 6), ("rent.", 7)]
_ti = B["term"]["first_word_idx"]          # '영어로는,' ; pay=+1 something=+2 in=+3 rent=+4
T_L1, T_L2 = ["pay", "~"], ["in", "rent"]
T_SZ = fit_sz([T_L1, T_L2], 740, 215)
TERM_ITEMS = (line_words(T_L1, T_SZ, 720, 456, _ti + 1, lambda i, t: "w" if i == 0 else "o", lambda i: (-640, 0) if i == 0 else (640, 0)) +
              line_words(T_L2, T_SZ, 960, 456, _ti + 3, lambda i, t: "w" if i == 0 else "o", lambda i: (-640, 0) if i == 0 else (0, 520)))
LBL_TXT, _lb = tmask("영어로는", 58); LBL_PM = rrect_mask(300, 86, 43, 30)
def scene_term(fr, t):
    t0 = BT[1]; slab(fr, 40, 350, 872, 1130, t, 2.0, 90)
    RX, RY, RW, RH = 30, 400, 860, 800
    act, gh = compose((RH, RW), TERM_ITEMS, t, RX, RY)
    if "o" in act:  # rent drips once landed
        rent = [it for it in TERM_ITEMS if it.txt == "rent"][0]
        if t > rent.t0 + .55:
            act["o"] = add_drips(act["o"], t - rent.t0 - .55, (.58, .72, .86, .95), 3, 60, 2.2, 15)
    draw_groups(fr, (RH, RW), RX, RY, act, gh, {"w": WW, "o": OR}, t, r=7, seed=1.0, wob_amp=2.5)
    p = t - t0; sc = 1 + .5 * math.exp(-p * 7) * math.cos(p * 13)
    pm = xform(LBL_PM, LBL_PM.shape[1] / 2, LBL_PM.shape[0] / 2, sc, sc, 0, 0, LBL_PM.shape); pm = goo(wob(pm, t, 1.5, 1, .05, 2), 2)
    draw_layer(fr, pm, 456 - pm.shape[1] / 2, 440 - pm.shape[0] / 2, OR, r=8, shadow=.4, spec=.8)
    h, w = LBL_TXT.shape; paste(fr, np.array(CH, F32), LBL_TXT, 456 - w / 2, 440 - h / 2 + 4)

# ---- meaning
_mi = B["meaning"]["first_word_idx"]       # 월세로 얼마를 내다, 라는 뜻이에요.
M_L1, M_L2 = ["월세로"], ["~를", "내다"]
M_SZ1 = fit_sz([M_L1], 740, 205); M_SZ2 = fit_sz([M_L2], 740, 170, gap=.3)
MEAN_ITEMS = (line_words(M_L1, M_SZ1, 700, 456, _mi, lambda i, t: "w", lambda i: (0, -480)) +
              [Wd("~를", M_SZ2, 456 - (tlen("~를", M_SZ2) + M_SZ2 * .3 + tlen("내다", M_SZ2)) / 2, 920, _mi + 1, "o", enter=(520, 0)),
               Wd("내다", M_SZ2, 456 - (tlen("~를", M_SZ2) + M_SZ2 * .3 + tlen("내다", M_SZ2)) / 2 + tlen("~를", M_SZ2) + M_SZ2 * .3, 920, _mi + 2, "o", enter=(0, 420))])
SUB_TXT, _sb = tmask("라는 뜻이에요", 52, "Bold"); SUB_PM = rrect_mask(int(tlen("라는 뜻이에요", 52, "Bold")) + 70, 84, 42, 30)
def scene_meaning(fr, t):
    slab(fr, 50, 400, 862, 1100, t, 3.0, 100)
    RX, RY, RW, RH = 40, 420, 840, 800
    act, gh = compose((RH, RW), MEAN_ITEMS, t, RX, RY)
    for grp, items, cols in (("w", [i for i in MEAN_ITEMS if i.grp == "w"], (.25, .6, .85)), ("o", [i for i in MEAN_ITEMS if i.grp == "o"], (.18, .45, .7, .92))):
        if grp in act and t > items[-1].t0 + .3 or (grp == "w" and t > MEAN_ITEMS[0].t0 + .3):
            act[grp] = add_drips(act[grp], t, cols, 4 if grp == "w" else 6, 50, 2.0 if grp == "w" else 2.4, 14)
    draw_groups(fr, (RH, RW), RX, RY, act, gh, {"w": WW, "o": OR}, t, r=7, seed=2.0, wob_amp=2.5)
    s9 = S(_mi + 3); p = t - s9; yb = 1010
    pm = SUB_PM; sc = 1 + .5 * math.exp(-max(p, 0) * 7) * math.cos(max(p, 0) * 13) if p > 0 else 1
    pm = goo(wob(xform(pm, pm.shape[1] / 2, pm.shape[0] / 2, sc, sc, 0, 0, pm.shape), t, 1.5, 2, .05, 2), 2)
    if p < 0: paste(fr, np.array(OR, F32), pm * .25, 456 - pm.shape[1] / 2, yb - pm.shape[0] / 2)
    else:
        draw_layer(fr, pm, 456 - pm.shape[1] / 2, yb - pm.shape[0] / 2, OR, r=8, shadow=.4, spec=.8)
        h, w = SUB_TXT.shape; paste(fr, np.array(CH, F32), SUB_TXT * min(1, p * 10), 456 - w / 2, yb - h / 2 + 5)

# ---- example (EN large, then EN small + KO)
EN_TOK = B["example_en"]["on_screen"].split(); _ei = B["example_en"]["first_word_idx"]
assert len(EN_TOK) == B["example_en"]["n_words"]
L1T, L2T = EN_TOK[:3], EN_TOK[3:]          # He pays $900 | a month in rent.
def en_layout(sz, y1, y2):
    its = line_words(L1T, sz, y1, 456, _ei, lambda i, t: "w" if i == 0 else "k") + line_words(L2T, sz, y2, 456, _ei + 3, lambda i, t: "k")
    return its
EN_SZ = fit_sz([L1T, L2T], 745, 100)
EN_BIG = en_layout(EN_SZ, 640, 640 + int(EN_SZ * 1.62))
EN_SM_SZ = 60; EN_SM = en_layout(EN_SM_SZ, 430, 430 + int(EN_SM_SZ * 1.62))
def box_mask(shape, items, sz, ox, oy, t, grow_t, static=False):
    """liquid orange box behind highlighted words (two lines -> merges via goo)."""
    M = np.zeros(shape, F32)
    for ln in ({it.yb for it in items}):
        its = [i for i in items if i.yb == ln and i.grp == "k"]
        if not its: continue
        x0 = min(i.x for i in its) - sz * .30; x1 = max(i.x + tlen(i.txt, sz) for i in its) + sz * .30
        y0 = ln - sz * .92; y1 = ln + sz * .30
        rm = rrect_mask(int(x1 - x0), int(y1 - y0), int((y1 - y0) / 2), 40); place(M, rm, x0 - ox - 40, y0 - oy - 40)
    if not static:
        p = (t - grow_t) / .45
        if p < 0: return M * 0
        cx = shape[1] / 2; cy = M.shape[0] / 2; sc = .65 + .35 * back(p)
        M = xform(M, cx, cy, sc, sc, 0, 0, shape) * min(1, p * 4)
    return M
def scene_en(fr, t, small=False):
    items = EN_SM if small else EN_BIG; sz = EN_SM_SZ if small else EN_SZ
    if small: slab(fr, 40, 300, 872, 620, t, 4.0, 80)
    else: slab(fr, 40, 460, 872, 940, t, 4.0, 90)
    RX, RY, RW, RH = 30, 280, 860, 860
    grow_t = S(_ei + 1) - .08
    Bx = box_mask((RH, RW), items, sz, RX, RY, t, grow_t, static=small)
    if Bx.max() > .01:
        Bx = add_drips(Bx, t, (.2, .45, .72, .92), 7, 44 if not small else 34, 2.2, 12 if not small else 9)
        Bx = goo(wob(Bx, t, 3, 4., .02, 1.8), 7, .5, .15)
        draw_layer(fr, Bx, RX, RY, OR, r=9, shadow=.5, spec=.9)
    boxed = t >= grow_t + .1 or small
    act, gh = compose((RH, RW), items, t, RX, RY)
    # words inside the box: ink CH ; outside: WW.  ghost of boxed words in CH when box exists
    cols = {"w": WW, "k": CH if boxed else WW}
    draw_groups(fr, (RH, RW), RX, RY, act, gh, cols, t, r=3, seed=3.0, wob_amp=1.5, shadow=.0 if boxed else .5,
                ghost=.3 if boxed else .24)
KO_TOK = B["example_ko"]["on_screen"].split(); _ki = B["example_ko"]["first_word_idx"]
assert len(KO_TOK) == B["example_ko"]["n_words"]
K1, K2 = KO_TOK[:4], KO_TOK[4:]
KO_SZ = fit_sz([K1, K2], 720, 82, gap=.3)
KO_ITEMS = (line_words(K1, KO_SZ, 840, 456, _ki, lambda i, t: "o" if i == 1 else "w", gap=.3) +
            line_words(K2, KO_SZ, 840 + int(KO_SZ * 1.7), 456, _ki + 4, lambda i, t: "o" if i == 0 else "w", gap=.3))
def scene_ko(fr, t):
    scene_en(fr, t, small=True)
    slab(fr, 40, 690, 872, 1130, t, 5.0, 90)
    RX, RY, RW, RH = 30, 700, 860, 440
    act, gh = compose((RH, RW), KO_ITEMS, t, RX, RY)
    draw_groups(fr, (RH, RW), RX, RY, act, gh, {"w": WW, "o": OR}, t, r=4, seed=4.0, wob_amp=2.0)

# ---- payoff
_pi = B["payoff"]["first_word_idx"]        # pay something in rent. 저장해 두세요.
P_L1, P_L2 = ["pay", "~"], ["in", "rent"]
P_SZ = fit_sz([P_L1, P_L2], 720, 225)
PAY_ITEMS = (line_words(P_L1, P_SZ, 640, 456, _pi, lambda i, t: "c") + line_words(P_L2, P_SZ, 640 + int(P_SZ * 1.2), 456, _pi + 2, lambda i, t: "c"))
BTN_W, BTN_H = 560, 150; BTN_PM = rrect_mask(BTN_W, BTN_H, 75, 40); BTN_TXT, _bb = tmask("저장해 두기", 66)
def bookmark_mask(w=64, h=92, pad=20):
    im = Image.new("L", (w + 2 * pad, h + 2 * pad), 0); ImageDraw.Draw(im).polygon([(pad, pad), (pad + w, pad), (pad + w, pad + h), (pad + w // 2, pad + int(h * .70)), (pad, pad + h)], fill=255)
    return blurf(np.asarray(im, F32) / 255, 1.2)
BOOK = bookmark_mask()
def scene_payoff(fr, t):
    t0 = BT[5]
    slab(fr, 40, 300, 872, 960, t, 6.0, 100, orange=True, drips=((.12, .35, .62, .88), 85))
    RX, RY, RW, RH = 30, 330, 860, 700
    act, gh = compose((RH, RW), PAY_ITEMS, t, RX, RY)
    draw_groups(fr, (RH, RW), RX, RY, act, gh, {"c": CH}, t, r=8, seed=5.0, wob_amp=3.0, shadow=0, ghost=.26)
    # save pill
    s1 = S(_pi + 4); p = t - s1; cx, cy = 62 + BTN_W / 2, 1105
    sc = 1 + .55 * math.exp(-max(p, 0) * 7) * math.cos(max(p, 0) * 13) if p > 0 else 1
    sc *= 1 + (.035 * math.sin(t * 7) if p > .6 else 0)
    pm = goo(wob(xform(BTN_PM, BTN_PM.shape[1] / 2, BTN_PM.shape[0] / 2, sc, sc, 0, 0, BTN_PM.shape), t, 2, 7, .04, 2.2), 3)
    ox_, oy_ = cx - pm.shape[1] / 2, cy - pm.shape[0] / 2
    if p < 0:
        paste(fr, np.array(SLABC, F32), pm * .5, ox_, oy_)
        ring = pm * (1 - sstep(.62, .92, blurf(pm, 8))); paste(fr, np.array(OR, F32), ring * .5, ox_, oy_)
        h, w = BTN_TXT.shape; paste(fr, np.array(WW, F32), BTN_TXT * .25, cx - w / 2 + 40, cy - h / 2 + 6)
    else:
        pm2 = add_drips(np.pad(pm, ((0, 120), (0, 0))), t, (.25, .6, .82), 9, 40, 2.3, 12); pm2 = goo(pm2, 3)
        paste(fr, np.array((8, 8, 8), F32), blurf(np.roll(pm2, 12, 0), 12) * .6, ox_, oy_)
        ring = pm2 * (1 - sstep(.62, .92, blurf(pm2, 8)))
        rgb = shade(pm2, SLABC, 14, .3, 30, amb=.85, dif=.25); rgb = rgb * (1 - ring[..., None]) + np.array(OR, F32)[None, None] * ring[..., None]
        paste(fr, rgb, pm2, ox_, oy_)
        bk = xform(BOOK, BOOK.shape[1] / 2, BOOK.shape[0] / 2, sc, sc, 0, 0, BOOK.shape)
        draw_layer(fr, bk, cx - BTN_W / 2 + 62 * sc - bk.shape[1] / 2 * 0 - 20, cy - bk.shape[0] / 2 + 2, OR, r=5, shadow=0, spec=.7)
        h, w = BTN_TXT.shape; paste(fr, np.array(WW, F32), BTN_TXT * min(1, p * 8), cx - w / 2 + 52, cy - h / 2 + 6)

# ------------------------------------------------------------------ frame assembly
def beat_idx(t): return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
SCENES = [scene_hook, scene_term, scene_meaning, lambda f, t: scene_en(f, t), scene_ko, scene_payoff]
TR = .34
def make_scene(bi, t):
    fr = background(t); SCENES[bi](fr, t); return fr
def render(i):
    t = i / FPS; bi = beat_idx(t); fr = make_scene(bi, t)
    if bi > 0 and t - BT[bi] < TR:
        p = (t - BT[bi]) / TR; old = make_scene(bi - 1, t)
        Y = -230 + (H + 460) * eo3(p)
        yy = np.arange(H, dtype=F32)[:, None]; xx = np.arange(W, dtype=F32)[None, :]
        edge = Y + 60 * np.sin(xx / 110 + t * 14) + 30 * np.sin(xx / 47 - t * 20)
        new = sstep(-3, 3, edge - 150 - yy)   # above band -> new scene
        band = sstep(-3, 3, edge - yy) * (1 - new)
        o = np.array(OR, F32); sh = np.clip(1 - (edge - yy) / 150, 0, 1)[..., None]
        bandc = o * (.55 + .45 * (1 - sh)) + 255 * np.clip(1 - np.abs((edge - yy) - 130) / 12, 0, 1)[..., None] * .55
        res = old * (1 - band[..., None] - new[..., None]) + bandc * band[..., None] + fr * new[..., None]
        fr = np.clip(res, 0, 255)
    draw_header(fr, t)
    fr = draw_bird(fr, i, t)
    draw_handle(fr)
    return np.clip(fr, 0, 255).astype(np.uint8)

def checks():
    pairs = [("hook number WW / charcoal slab-or-bg dark", WW, CH), ("hook number WW / orange ring+rim (worst case)", WW, OR),
             ("sentence & example plain WW / slab", WW, SLABC), ("orange text OR / slab", OR, SLABC),
             ("highlight ink CH / orange box", CH, OR), ("payoff ink CH / orange slab", CH, OR), ("chip/label ink CH / orange pill", CH, OR),
             ("handle WW / charcoal backing", WW, (10, 10, 10)), ("pill text WW / slab", WW, SLABC)]
    for n, a, b in pairs: print(f"contrast {n}: {contrast(a, b):.2f}")
    print("number size", NUM_SZ, "term sz", T_SZ, "meaning sz", M_SZ1, M_SZ2, "en sz", EN_SZ, "ko sz", KO_SZ, "payoff sz", P_SZ)

if __name__ == "__main__":
    checks()
    if "--frames" in sys.argv:
        for ts in sys.argv[sys.argv.index("--frames") + 1].split(","):
            Image.fromarray(render(int(round(float(ts) * FPS)))).save(f"{FR}/kw_{RID}_t{ts}.png")
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
