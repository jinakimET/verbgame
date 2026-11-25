#!/usr/bin/env python3
"""kw_12 'so ~ that' v4 (2026-11-25 episode): SOFT CLAYMORPHISM, restrained.
Palette: cream bg / sage / warm clay / near-black ink. Key image = tiny clay room in front of a grand palace silhouette
(ex2: moon + clay train with a sleepy passenger, wordless). Single bigger effect = the answer beat 'so ~ that'.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw4_12.py [--frames t1,t2,...]"""
import os, sys, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
RID = "12"; W, H = 1080, 1920; FPS = 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels/v4"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
MP3 = f"{ROOT}/audio/v3/kw_{RID}.mp3"
FD = "/usr/share/fonts/opentype/noto/NotoSansCJK-"
_fc = {}
def font(sz, w="Bold"):
    k = (sz, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}{w}.ttc", sz, index=1)
    return _fc[k]

CREAM = (241, 235, 220); CREAM2 = (231, 224, 205)
SAGE = (160, 178, 143); SAGE_D = (118, 138, 106); PANEL = (226, 232, 213)
CLAY = (201, 142, 110); CLAY_D = (170, 112, 86); CLAY_L = (232, 196, 170)
INK = (43, 40, 36); GREY = (88, 84, 76); MOON = (232, 212, 160)
def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

D = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[RID]
words = D["words"]; BEATS = D["beats"]
MINLEN = []
for i, w in enumerate(words):
    if w["e"] - w["s"] < .08: MINLEN.append((i, w["t"]))
AUDIO_DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
TOTAL = AUDIO_DUR + TAIL; NF = int(round(TOTAL * FPS))
def ws(i): return words[i]["s"]

# ---------------------------------------------------------------- helpers
PAD = 60
def blur(L, r): return L.filter(ImageFilter.GaussianBlur(r))
def put(img, spr, x, y):
    x, y = int(round(x)), int(round(y)); sw, sh = spr.size
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(img.width, x + sw), min(img.height, y + sh)
    if x1 <= x0 or y1 <= y0: return
    img.alpha_composite(spr.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))
def fade(spr, a):
    if a >= .999: return spr
    s = spr.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * max(0, a)))); return s
def ease(p):
    p = min(1, max(0, p)); return p * p * (3 - 2 * p)
def scaled(spr, s):
    return spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.BILINEAR)
def mask_draw(w, h, fn, pad=PAD):
    ss = 2; im = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0); d = ImageDraw.Draw(im)
    fn(d, pad * ss, ss); return im.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
def rrect(w, h, r, pad=PAD):
    return mask_draw(w, h, lambda d, p, s: d.rounded_rectangle((p, p, p + w * s, p + h * s), radius=r * s, fill=255), pad)
def clay(mask, col, d=None, shadow=True, sh_alpha=.22, sh_off=(0, 14), sh_blur=14, hi=.5, lo=.22):
    bb = mask.getbbox(); bw, bh = bb[2] - bb[0], bb[3] - bb[1]; ms = min(bw, bh)
    d = d or max(3, int(ms * .05)); r = d * 1.3
    m = np.asarray(mask, np.float32) / 255
    a1 = np.asarray(blur(ImageChops.offset(mask, d, d), r), np.float32) / 255
    a2 = np.asarray(blur(ImageChops.offset(mask, -d, -d), r), np.float32) / 255
    pf = np.asarray(blur(mask, max(2, ms * .22)), np.float32) / 255
    hl = m * (1 - a1); sh = m * (1 - a2)
    c = np.array(col, np.float32)[None, None, :]
    rgb = c * (1 + .10 * (pf[..., None] - .55)) + (255 - c) * (hl[..., None] * hi) - c * (sh[..., None] * lo)
    spr = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.asarray(mask, np.float32)]).astype(np.uint8), "RGBA")
    if not shadow: return spr
    sm = blur(ImageChops.offset(mask, sh_off[0], sh_off[1]), sh_blur).point(lambda v: int(v * sh_alpha))
    base = Image.new("RGBA", mask.size, (60, 50, 40, 0)); base.putalpha(sm); base.alpha_composite(spr); return base
def pill(w, h, col, r=None, d=None, **kw):
    return clay(rrect(w, h, r or h // 2), col, d=d, **kw)

# ---------------------------------------------------------------- background
def build_bg():
    y = np.linspace(0, 1, H)[:, None, None]
    g = np.array(CREAM, np.float32) * (1 - y) + np.array(CREAM2, np.float32) * y
    g = np.broadcast_to(g, (H, W, 3)).astype(np.uint8)
    im = Image.fromarray(np.ascontiguousarray(g)).convert("RGBA")
    # faint sage disc behind the key image
    disc = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(disc).ellipse((86, 238, 826, 778), fill=SAGE + (46,))
    im.alpha_composite(blur(disc, 6) if False else disc)
    return im
BG = build_bg()

# ---------------------------------------------------------------- key image A: tiny clay room + palace silhouette
PW, PH = 640, 380
def palace_mask():
    def fn(d, p, s):
        R = lambda x0, y0, x1, y1, r=0: d.rounded_rectangle((p + x0 * s, p + y0 * s, p + x1 * s, p + y1 * s), radius=r * s, fill=255)
        R(20, 340, 620, 368, 8); R(50, 316, 590, 342, 6)
        R(40, 232, 200, 320, 4); R(440, 232, 600, 320, 4); R(30, 216, 210, 236, 6); R(430, 216, 610, 236, 6)
        R(200, 170, 440, 320, 4)
        d.polygon([(p + 186 * s, p + 174 * s), (p + 454 * s, p + 174 * s), (p + 320 * s, p + 122 * s)], fill=255)
        R(272, 96, 368, 128, 6); d.ellipse((p + 258 * s, p + 28 * s, p + 382 * s, p + 128 * s), fill=255)
        R(316, 4, 324, 36, 3); d.ellipse((p + 311 * s, p + 0 * s, p + 329 * s, p + 14 * s), fill=255)
        for cx in (90, 150, 490, 550):
            d.ellipse((p + (cx - 26) * s, p + 176 * s, p + (cx + 26) * s, p + 236 * s), fill=255)
        # windows (cut-outs)
        for x in (225, 285, 345, 392):
            d.rounded_rectangle((p + x * s, p + 200 * s, p + (x + 26) * s, p + 272 * s), radius=13 * s, fill=0)
        for x in (70, 130, 470, 530):
            d.rounded_rectangle((p + x * s, p + 262 * s, p + (x + 22) * s, p + 306 * s), radius=11 * s, fill=0)
        d.rounded_rectangle((p + 300 * s, p + 276 * s, p + 340 * s, p + 320 * s), radius=20 * s, fill=0)
    return mask_draw(PW, PH, fn)
PALACE = clay(palace_mask(), SAGE, d=6, sh_alpha=.2, sh_off=(0, 12), sh_blur=14)
def room_composite():
    w, h = 190, 170; spr = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    # body rect at (50..,..) built directly with mask so geometry is explicit
    def bf(d, p, s):
        d.rounded_rectangle((p + 12 * s, p + 66 * s, p + 178 * s, p + 160 * s), radius=12 * s, fill=255)
    body = clay(mask_draw(190, 170, bf, 40), CLAY, d=5, shadow=True, sh_alpha=.3, sh_off=(0, 10), sh_blur=10)
    def rf(d, p, s):
        d.polygon([(p + 0 * s, p + 70 * s), (p + 95 * s, p + 6 * s), (p + 190 * s, p + 70 * s)], fill=255)
    roof = clay(mask_draw(190, 170, rf, 40), CLAY_D, d=5, shadow=False)
    def wf(d, p, s): d.rounded_rectangle((p + 108 * s, p + 92 * s, p + 152 * s, p + 128 * s), radius=8 * s, fill=255)
    win = clay(mask_draw(190, 170, wf, 40), (246, 232, 196), d=3, shadow=False, hi=.3)
    def df(d, p, s): d.rounded_rectangle((p + 42 * s, p + 100 * s, p + 82 * s, p + 160 * s), radius=18 * s, fill=255)
    door = clay(mask_draw(190, 170, df, 40), (126, 88, 68), d=3, shadow=False, hi=.2)
    for s_ in (body, roof, win, door): spr.alpha_composite(s_, (0, 0))
    return spr
ROOM = room_composite()

# ---------------------------------------------------------------- key image B: moon + clay train with sleepy passenger
def build_scene_b():
    S = Image.new("RGBA", (760, 520), (0, 0, 0, 0)); P2 = 0
    # moon (crescent)
    def mf(d, p, s):
        d.ellipse((p + 0 * s, p + 0 * s, p + 150 * s, p + 150 * s), fill=255)
        d.ellipse((p + 46 * s, p + -14 * s, p + 176 * s, p + 116 * s), fill=0)
    moon = clay(mask_draw(180, 150, mf, 40), MOON, d=5, sh_alpha=.15)
    S.alpha_composite(moon, (160 - 40, 30 - 40))
    for (x, y, r) in ((370, 60, 7), (470, 120, 5), (300, 150, 5), (560, 50, 6)):
        dd = ImageDraw.Draw(S); dd.ellipse((x - r, y - r, x + r, y + r), fill=MOON + (255,))
    # rails
    rail = pill(700, 14, SAGE_D, r=7, d=3, shadow=False); S.alpha_composite(rail, (30 - PAD, 440 - PAD))
    def car(col, w, h, r=22):
        return pill(w, h, col, r=r, d=6, sh_alpha=.25, sh_off=(0, 10), sh_blur=10)
    cw, chh = 190, 128
    xs = [60, 275]
    for x in xs:
        c = car(SAGE, cw, chh); S.alpha_composite(c, (x - PAD, 296 - PAD))
        wn = pill(72, 64, (246, 238, 214), r=16, d=3, shadow=False, hi=.25); S.alpha_composite(wn, (x + 20 - PAD, 316 - PAD))
        wn2 = pill(56, 64, (246, 238, 214), r=16, d=3, shadow=False, hi=.25); S.alpha_composite(wn2, (x + 118 - PAD, 316 - PAD))
    eng = car(CLAY, 200, 150, r=26); S.alpha_composite(eng, (490 - PAD, 274 - PAD))
    chim = pill(40, 54, CLAY_D, r=10, d=4, shadow=False); S.alpha_composite(chim, (520 - PAD, 236 - PAD))
    ewn = pill(64, 60, (246, 238, 214), r=14, d=3, shadow=False, hi=.25); S.alpha_composite(ewn, (594 - PAD, 298 - PAD))
    dd = ImageDraw.Draw(S)
    for cx in (110, 220, 330, 400, 540, 640):
        dd.ellipse((cx - 22, 420 - 0, cx + 22, 464), fill=INK + (255,)); dd.ellipse((cx - 8, 434, cx + 8, 450), fill=CREAM + (255,))
    # sleepy passenger in the first car window (closed eyes, no text)
    hx, hy = 60 + 56, 316 + 34
    dd.ellipse((hx - 25, hy - 24, hx + 25, hy + 26), fill=CLAY_L + (255,))
    for ex in (hx - 10, hx + 10):
        dd.arc((ex - 6, hy - 6, ex + 6, hy + 6), 20, 160, fill=INK + (255,), width=3)
    dd.arc((hx - 6, hy + 8, hx + 6, hy + 18), 200, 340, fill=INK + (255,), width=3)
    return S
SCENE_B = build_scene_b()

# ---------------------------------------------------------------- text blocks
PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 62, 790, 788, 480
PANEL_SPR = pill(PANEL_W, PANEL_H, PANEL, r=70, d=8, sh_alpha=.25)
TXT_W = 690; CY0 = PANEL_Y + PANEL_H / 2

def tok_sprite(t, sz, col, wt_="Bold"):
    f = font(sz, wt_); w = int(f.getlength(t)) + 12
    im = Image.new("RGBA", (w, int(sz * 1.7)), (0, 0, 0, 0)); ImageDraw.Draw(im).text((6, int(sz * 1.2)), t, font=f, fill=col + (255,), anchor="ls"); return im
def make_block(tokens, sz, col, wt_="Bold", maxw=TXT_W, lh_k=1.5):
    """tokens: (text, ts, hl). Returns dict(lines=[...], height) with layout relative to block top, x relative to panel centre."""
    f = font(sz, wt_); sp = f.getlength(" ") + 2; lines = [[]]; cur = 0
    for tk in tokens:
        wd = f.getlength(tk[0])
        if lines[-1] and cur + sp + wd > maxw: lines.append([]); cur = 0
        cur += (sp if lines[-1] else 0) + wd; lines[-1].append(tk)
    LH = int(sz * lh_k); items = []; pills = []
    for li, ln in enumerate(lines):
        tot = sum(f.getlength(t[0]) for t in ln) + sp * (len(ln) - 1); x = -tot / 2; y = li * LH
        xs = []
        for tk in ln: xs.append(x); x += f.getlength(tk[0]) + sp
        k = 0
        while k < len(ln):
            if ln[k][2]:
                j = k
                while j + 1 < len(ln) and ln[j + 1][2]: j += 1
                gx0 = xs[k] - max(5, sz * .12); gx1 = xs[j] + f.getlength(ln[j][0]) + max(5, sz * .12); ph = int(sz * 1.3)
                pills.append((pill(int(gx1 - gx0), ph, CLAY_L, r=ph // 2, d=4, shadow=False, hi=.35), gx0 - PAD, y + int(sz * .02) - PAD, ln[k][1]))
                k = j + 1
            else: k += 1
        for tk, x in zip(ln, xs):
            items.append((tok_sprite(tk[0], sz, col, wt_), x - 6, y + int(sz * 1.05) - int(sz * 1.2), tk[1]))
    return dict(items=items, pills=pills, h=LH * len(lines) - (LH - int(sz * 1.35)))
def fit_block(tokens, col, maxh, sizes, wt_="Bold"):
    for sz in sizes:
        b = make_block(tokens, sz, col, wt_)
        if b["h"] <= maxh: return b
    return b

def toks(beat, texts_idx, hl=()):
    """map show tokens to word start times via index map"""
    return None
def beat_tokens(b, hl=()):
    sh = b["show"].split(); i0 = b["first_word_idx"]; role = b["role"]; r = []
    for k, t in enumerate(sh):
        if role == "hook" and b is BEATS[0]: wi = 0 if k == 0 else k + 2
        elif role == "answer": wi = {0: 0, 1: 1, 2: 1, 3: 2}[k]
        else:
            assert len(sh) == b["n_words"], (role, sh); wi = k
        r.append((t, ws(i0 + wi), k in hl))
    return r

BLOCKS = []   # per beat: list of (block, y_top)
def stack(parts, gap=22):
    tot = sum(p[0]["h"] for p in parts) + gap * (len(parts) - 1); y = CY0 - tot / 2; out = []
    for blk, dim in parts: out.append((blk, y, dim)); y += blk["h"] + gap
    return out
HL = {"question": (1, 2, 3), "meaning": (0, 1, 2), "ex1_en": (3, 4, 5), "ex1_ko": (1, 2), "ex2_en": (2, 3, 4), "ex2_ko": (1, 2)}
for bi, b in enumerate(BEATS):
    role = b["role"]
    if role == "answer": BLOCKS.append(None); continue
    tk = beat_tokens(b, HL.get(role, ()))
    if role in ("ex1_ko", "ex2_ko"):
        en = beat_tokens(BEATS[bi - 1], HL[BEATS[bi - 1]["role"]])
        en_blk = make_block(en, 40, GREY); ko_blk = fit_block(tk, INK, 280, range(84, 50, -2))
        BLOCKS.append(stack([(en_blk, True), (ko_blk, False)], gap=34))
    elif role == "meaning":
        BLOCKS.append(stack([(fit_block(tk, INK, 300, range(88, 50, -2)), False)]))
    else:
        BLOCKS.append(stack([(fit_block(tk, INK, 400, range(84, 44, -2)), False)]))

# answer beat layout
AN = BEATS[3]; AI0 = AN["first_word_idx"]
T_ANS, T_SO, T_THAT = ws(AI0), ws(AI0 + 1), ws(AI0 + 2)
AN_LABEL = tok_sprite("정답은…", 64, GREY)
ANS_SZ = 150; _f = font(ANS_SZ, "Black"); _sp = _f.getlength(" ") + 14
_w = [_f.getlength("so"), _f.getlength("~"), _f.getlength("that")]; ANS_TOT = sum(_w) + 2 * _sp
ANS_PILL = pill(int(ANS_TOT + 90), 230, CLAY_L, r=115, d=9, sh_alpha=.28)
ANS_SPR = [tok_sprite("so", ANS_SZ, INK, "Black"), tok_sprite("~", ANS_SZ, INK, "Black"), tok_sprite("that", ANS_SZ, INK, "Black")]
ANS_X = []; _x = -ANS_TOT / 2
for wd in _w: ANS_X.append(_x); _x += wd + _sp
ANS_CY = CY0 + 40

HANDLE = Image.new("RGBA", (W, 60), (0, 0, 0, 0)); ImageDraw.Draw(HANDLE).text((W // 2 - 60, 30), "지나쌤영어  @jina.ssam_english", font=font(34, "Bold"), fill=INK + (255,), anchor="mm")
BENV = bird.envelope(MP3, FPS, NF)

BT = [b["start"] for b in BEATS]
def beat_idx(t): return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
GHOST = .20

def draw_block(img, stk, t, t0, alpha=1.0, prog_ghost=True):
    cx = PANEL_X + PANEL_W / 2
    gh = GHOST * (min(1, (t - t0) / .3) if t0 > 0 else 1.0)
    for blk, y, dim in stk:
        for spr, px, py, ts in blk["pills"]:
            q = ease((t - ts) / .3); a = (gh * .5 + (1 - gh * .5) * q) * alpha if not dim else alpha * .85
            put(img, fade(spr, a), cx + px, y + py)
        for spr, px, py, ts in blk["items"]:
            if dim: put(img, fade(spr, alpha), cx + px, y + py); continue
            q = ease((t - ts) / .22)
            a = (gh + (1 - gh) * q) * alpha
            put(img, fade(spr, a), cx + px, y + py + 8 * (1 - q))

def draw_answer(img, t, alpha=1.0):
    cx = PANEL_X + PANEL_W / 2; gh = GHOST * min(1, (t - T_ANS) / .3)
    q0 = ease((t - T_ANS) / .22); put(img, fade(AN_LABEL, (gh + (1 - gh) * q0) * alpha), cx - AN_LABEL.width / 2, PANEL_Y + 90)
    # the one bigger effect: the clay pill rises/swells slowly under so ~ that
    p = ease((t - T_SO) / 1.0); sc = .86 + .14 * p
    if t >= T_SO - .6:
        pl = scaled(ANS_PILL, sc); put(img, fade(pl, (.35 + .65 * p) * alpha), cx - pl.width / 2, ANS_CY - pl.height / 2 + (1 - p) * 14)
    for k, (spr, x) in enumerate(zip(ANS_SPR, ANS_X)):
        ts = T_SO if k < 2 else T_THAT
        q = ease((t - ts) / .3); a = (gh + (1 - gh) * q) * alpha
        put(img, fade(spr, a), cx + x - 6, ANS_CY - int(ANS_SZ * 1.2) + int(ANS_SZ * .6) - 14 + (1 - q) * 10)

def draw_key(img, t):
    bob = 3 * math.sin(t * 1.3)
    t_b = BT[7]
    mixB = ease((t - (t_b - .1)) / .9)
    # palace emphasis on the words 'palace' / 궁궐처럼 (soft, no flash)
    pal_t = [ws(BEATS[1]["first_word_idx"] + 5), ws(BEATS[5]["first_word_idx"] + 11), ws(BEATS[6]["first_word_idx"] + 6)]
    emph = max([ease((t - x) / .8) * (1 - ease((t - x - 2.2) / 1.2)) for x in pal_t] + [0])
    ax = 1 - mixB
    if ax > .01:
        pa = (.62 + .38 * emph) * ax
        put(img, fade(PALACE, pa), 456 - PALACE.width / 2, 300 - PAD + bob * .6 - 8 * emph)
        rs = 1.0 + .08 * emph
        r = scaled(ROOM, rs) if rs > 1.001 else ROOM
        put(img, fade(r, ax), 456 - r.width / 2, 730 - r.height + 14 + bob * .4)
    if mixB > .01:
        put(img, fade(SCENE_B, mixB), 456 - SCENE_B.width / 2 + 10, 250 + bob)

def render(i):
    t = i / FPS; bi = beat_idx(t); t0 = BT[bi]; role = BEATS[bi]["role"]
    img = BG.copy()
    draw_key(img, t)
    put(img, PANEL_SPR, PANEL_X - PAD, PANEL_Y - PAD)
    # previous beat fading out
    if bi > 0 and t - t0 < .25:
        pb = bi - 1; k = 1 - ease((t - t0) / .25)
        if BEATS[pb]["role"] == "answer": draw_answer(img, t, k)
        else: draw_block(img, BLOCKS[pb], t, BT[pb], alpha=k)
    if role == "answer": draw_answer(img, t)
    else: draw_block(img, BLOCKS[bi], t, t0)
    a = float(BENV[min(i, len(BENV) - 1)])
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bird.place(lay, a, 170, 1532)
    img.alpha_composite(lay)
    put(img, HANDLE, 0, 1558)
    return img.convert("RGB")

def checks():
    for n, a_, b_ in (("ink/panel", INK, PANEL), ("ink/clay_l pill on panel", INK, CLAY_L), ("grey/panel", GREY, PANEL), ("grey/clay_l", GREY, CLAY_L),
                      ("clay_d ~ / clay_l", CLAY_D, CLAY_L), ("ink/cream handle", INK, CREAM2), ("ink/clay_l (answer)", INK, CLAY_L)):
        print(f"contrast {n}: {contrast(a_, b_):.2f}")
    print("min-length corrected words:", MINLEN or "none", "| total", TOTAL, "frames", NF)

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
        if i % 120 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait(); print("done", outp)
