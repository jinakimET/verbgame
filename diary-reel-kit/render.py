import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import math, sys, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, _HERE)
from timing import build
from mouth import warp, CH as CHAR0

W, H, FPS, DUR = 1080, 1920, 30, 27.1
ROOT = _HERE + "/"

# ---------- palette (Color Hunt 1E3B2F 7F8C6A C8B48A F5F0E6) ----------
from palette import BG, INK, INK_SOFT, LAV, ROSE, MARK, CARD, SUN, LEAVES, WHITE

F = "/usr/share/fonts/opentype/inter/"
KR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
KRM = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
def inter(sz, w="SemiBold"): return ImageFont.truetype(F + f"InterDisplay-{w}.otf", sz)
def kr(sz, med=False): return ImageFont.truetype(KRM if med else KR, sz, index=1)

FONT_EN = inter(60); FONT_EN_BIG = inter(96, "Bold")
FONT_KO = kr(42)
FONT_LABEL = inter(28, "Bold"); FONT_LABEL_KR = kr(28)
FONT_CARD_EN = inter(54, "Bold"); FONT_CARD_KO = kr(40); FONT_CARD_TAG = kr(26, True)

SENTS = build()

# ---------- easing ----------
def clamp(x, a=0, b=1): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in_out(x): x = clamp(x); return x * x * (3 - 2 * x)
def pop(x):  # slight overshoot
    x = clamp(x); c = 1.6
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------- audio envelope for mouth ----------
def load_env():
    with wave.open(ROOT + "voice_pad.wav") as w:
        n = w.getnframes(); sr = w.getframerate()
        a = np.frombuffer(w.readframes(n), np.int16).reshape(-1, 2)[:, 0].astype(np.float32) / 32768
    hop = sr // FPS; win = int(sr * 0.045)
    nf = int(DUR * FPS) + 2
    env = np.zeros(nf)
    for i in range(nf):
        c = i * hop; seg = a[max(0, c - win // 2): c + win // 2]
        env[i] = np.sqrt((seg ** 2).mean()) if len(seg) else 0
    env = env / np.percentile(env, 97)
    sm = np.zeros_like(env); v = 0
    for i, e in enumerate(env):  # fast attack, softer release
        v = v + (e - v) * (0.75 if e > v else 0.35); sm[i] = v
    return np.clip(sm, 0, 1.2)
ENV = load_env()
def env_at(t): return float(ENV[min(len(ENV) - 1, max(0, int(round(t * FPS))))])

# ---------- static layers ----------
def make_bg():
    im = Image.new("RGB", (W, H), BG)
    rng = np.random.default_rng(3)
    noise = (rng.normal(0, 4, (H, W, 1))).astype(np.int16)
    arr = np.clip(np.array(im).astype(np.int16) + noise, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr)
    glow = Image.new("L", (W, H), 0); d = ImageDraw.Draw(glow)
    d.ellipse((140, 640, 940, 1440), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    im.paste(Image.new("RGB", (W, H), SUN), (0, 0), glow.point(lambda v: int(v * 0.85)))
    return im.convert("RGBA")
BGIMG = make_bg()

def leaf_sprite(col, size):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = []
    hw, hh = s * 0.30, s * 0.44
    for k in range(0, 181, 5):
        u = math.radians(k)
        pts.append((s / 2 + math.sin(u) ** 1.3 * hw, s / 2 - math.cos(u) * hh))
    for k in range(180, -1, -5):
        u = math.radians(k)
        pts.append((s / 2 - math.sin(u) ** 1.3 * hw * 0.92, s / 2 - math.cos(u) * hh))
    d.polygon(pts, fill=col + (235,))
    d.line([(s / 2, s * 0.1), (s / 2, s * 0.92)], fill=tuple(int(c * 0.7) for c in col) + (255,), width=max(2, s // 40))
    return im.resize((size, size), Image.LANCZOS)
LEAFSPR = [leaf_sprite(LEAVES[i % 4], sz) for i, sz in enumerate([78, 60, 86, 54, 70, 64, 50])]
LEAFP = [(110, 0.00, 1, 2), (930, 0.30, 1, 3), (300, 0.55, 1, 2), (780, 0.75, 1, 4),
         (60, 0.42, 1, 3), (1000, 0.12, 1, 2), (560, 0.88, 1, 3)]

def draw_leaves(img, t, boost=1.0):
    span = H + 240
    for spr, (x0, ph, n, m) in zip(LEAFSPR, LEAFP):
        prog = (t / DUR * n + ph) % 1.0       # one full fall per video -> seamless loop
        y = -120 + prog * span
        x = x0 + 40 * math.sin(2 * math.pi * (t / DUR * m + ph * 3))
        ang = 35 * math.sin(2 * math.pi * (t / DUR * (m + 1) + ph))
        r = spr.rotate(ang, resample=Image.BICUBIC, expand=True)
        if boost < 1:
            r = r.copy(); r.putalpha(r.getchannel("A").point(lambda v: int(v * boost)))
        img.alpha_composite(r, (int(x - r.width / 2), int(y - r.height / 2)))

# ---------- character ----------
CS = 1010 / CHAR0.shape[0]           # scale
CW, CHH = int(CHAR0.shape[1] * CS), int(CHAR0.shape[0] * CS)
CX, CTOP = 540, 560
BULB = (495, 240)
FADE = np.clip((CHH - 1 - np.arange(CHH)) / 140.0, 0, 1)[:, None]
def card_events():
    ev = []
    for s in SENTS:
        for c in s["cards"]: ev.append(c["t"])
    return ev
CARD_T = card_events()

def char_layer(t, mouth_open, hop):
    arr = warp(mouth_open)
    im = Image.fromarray(arr).resize((CW, CHH), Image.LANCZOS)
    im.putalpha(Image.fromarray((np.array(im.getchannel("A")).astype(np.float32) * FADE).astype(np.uint8)))
    breathe = 1 + 0.008 * math.sin(2 * math.pi * t / 3.0)
    sway = 1.3 * math.sin(2 * math.pi * t / 6.0) + 0.6 * math.sin(2 * math.pi * t / 4.0)
    e = env_at(t)
    sway += 1.2 * e * math.sin(2 * math.pi * t * 1.5)
    sw, sh = int(CW * (1 + 0.004 * e)), int(CHH * breathe)
    im = im.resize((sw, sh), Image.BILINEAR)
    im = im.rotate(sway, resample=Image.BICUBIC, expand=True, center=(sw / 2, sh))
    dy = -8 * e - hop
    x = int(CX - im.width / 2); y = int(CTOP + CHH - sh - (im.height - sh) / 2 + dy)
    return im, x, y, sway

def hop_at(t):
    h = 0
    for ct in CARD_T:
        d = t - ct
        if 0 <= d < 0.9: h += 26 * math.exp(-d * 6) * math.sin(d * 14 + 0.2) * (1 if d * 14 < math.pi else 0.35)
    return max(0, h)

def bulb_glow(img, t, cx, cy):
    g = 0.25 + 0.15 * math.sin(2 * math.pi * t / 3)
    for ct in CARD_T:
        d = t - ct
        if 0 <= d < 1.2: g += 0.9 * math.exp(-d * 3)
    r = int(120 + 40 * min(1, g))
    lay = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(lay).ellipse((r * 0.35, r * 0.35, r * 1.65, r * 1.65), fill=255)
    lay = lay.filter(ImageFilter.GaussianBlur(r * 0.25)).point(lambda v: int(v * clamp(g, 0, 1) * 0.9))
    col = Image.new("RGBA", lay.size, (255, 226, 120, 0)); col.putalpha(lay)
    img.alpha_composite(col, (int(cx - r), int(cy - r)))

# ---------- text helpers ----------
def tw(font, s): return font.getlength(s)

def layout_words(words, font, maxw, line_h):
    lines = [[]]; x = 0; sp = tw(font, " ")
    for i, w in enumerate(words):
        wl = tw(font, w)
        if lines[-1] and x + wl > maxw:
            lines.append([]); x = 0
        lines[-1].append((i, x, wl)); x += wl + sp
    return lines

def draw_sentence(img, s, unit, t, alpha, yoff):
    words = [s["words"][i]["w"] for i in unit["idx"]]
    font = FONT_EN_BIG if s["big"] else FONT_EN
    lh = int(font.size * (1.18 if s["big"] else 1.3))
    maxw = 940
    lines = layout_words(words, font, maxw, lh)
    asc, desc = font.getmetrics()
    block_h = len(lines) * lh
    top = (430 if s["big"] else 400) - block_h / 2 + yoff
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    card_words = set()
    for c in s["cards"]:
        for k in range(c["i0"], c["i1"] + 1): card_words.add(k)
    for li, line in enumerate(lines):
        lw = line[-1][1] + line[-1][2]
        x0 = (W - lw) / 2
        y = top + li * lh
        for (j, x, wl) in line:
            gi = unit["idx"][j]; wd = s["words"][gi]
            spoken = t >= wd["s"]
            cur = wd["s"] <= t < wd["e"] + 0.04
            # marker
            mk = 0
            if gi in card_words and spoken: mk = 1
            elif cur: mk = ease_out((t - wd["s"]) / 0.10)
            if mk > 0:
                pad = 8
                mx0 = x0 + x - pad; mx1 = x0 + x - pad + (wl + 2 * pad) * mk
                my0 = y + asc * 0.38; my1 = y + asc + desc * 0.55
                d.rounded_rectangle((mx0, my0, mx1, my1), radius=10, fill=MARK + (int(235 * alpha),))
        for (j, x, wl) in line:
            gi = unit["idx"][j]; wd = s["words"][gi]
            a = 1.0 if t >= wd["s"] else 0.36
            d.text((x0 + x, y), wd["w"], font=font, fill=INK + (int(255 * a * alpha),))
    img.alpha_composite(lay)

def draw_korean(img, text, alpha, yoff=0):
    lines = text.split("\n")
    lh = 60
    widths = [tw(FONT_KO, l) for l in lines]
    bw = max(widths) + 80; bh = len(lines) * lh + 44
    cy = 1590 + yoff
    x0 = (W - bw) / 2; y0 = cy - bh / 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
    d.rounded_rectangle((x0, y0 + 10, x0 + bw, y0 + bh + 10), radius=30, fill=(90, 60, 30, int(45 * alpha)))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(sh)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=30, fill=WHITE + (int(250 * alpha),))
    for i, l in enumerate(lines):
        d.text(((W - widths[i]) / 2, y0 + 18 + i * lh), l, font=FONT_KO, fill=INK + (int(255 * alpha),))
    img.alpha_composite(lay)

_card_cache = {}
def card_sprite(en, ko):
    key = (en, ko)
    if key in _card_cache: return _card_cache[key]
    tag = "오늘의 표현"
    w = int(max(tw(FONT_CARD_EN, en), tw(FONT_CARD_KO, ko), 300) + 90)
    h = 220
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 42, 30 + w, 42 + h), radius=36, fill=(110, 60, 20, 70))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((30, 30, 30 + w, 30 + h), radius=36, fill=CARD + (255,))
    tg = tw(FONT_CARD_TAG, tag)
    d.rounded_rectangle((30 + (w - tg) / 2 - 20, 48, 30 + (w + tg) / 2 + 20, 92), radius=22, fill=WHITE + (255,))
    d.text((30 + (w - tg) / 2, 51), tag, font=FONT_CARD_TAG, fill=INK)
    d.text((30 + (w - tw(FONT_CARD_EN, en)) / 2, 104), en, font=FONT_CARD_EN, fill=INK)
    d.text((30 + (w - tw(FONT_CARD_KO, ko)) / 2, 172), ko, font=FONT_CARD_KO, fill=(92, 52, 24))
    _card_cache[key] = im
    return im

def draw_card(img, c, t, t_end):
    d_in = t - c["t"]
    if d_in < 0 or t > t_end + 0.2: return
    sc = 0.82 + 0.18 * pop(d_in / 0.34)
    al = ease_out(d_in / 0.18)
    if t > t_end:
        k = (t - t_end) / 0.2
        al *= 1 - ease_out(k); sc *= 1 - 0.05 * k
    spr = card_sprite(c["en"], c["ko"])
    ang = -2.2 * (1 - ease_out(d_in / 0.5)) - 1.0
    s = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BICUBIC)
    s = s.rotate(ang, resample=Image.BICUBIC, expand=True)
    if al < 1: s.putalpha(s.getchannel("A").point(lambda v: int(v * al)))
    img.alpha_composite(s, (int(540 - s.width / 2), int(1330 - s.height / 2)))

def draw_label(img, alpha=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a = "MY ENGLISH DIARY"; b = "  ·  가을 편"
    wa, wb = tw(FONT_LABEL, a), tw(FONT_LABEL_KR, b)
    x0 = (W - wa - wb) / 2 - 26
    d.rounded_rectangle((x0, 166, x0 + wa + wb + 52, 218), radius=26, outline=INK + (int(200 * alpha),), width=3)
    d.text((x0 + 26, 175), a, font=FONT_LABEL, fill=INK + (int(255 * alpha),))
    d.text((x0 + 26 + wa, 170), b, font=FONT_LABEL_KR, fill=INK + (int(255 * alpha),))
    img.alpha_composite(lay)

# ---------- ending panel ----------
END_T0 = 21.54
LOOP_T0 = 26.35
END_LINES = [
    ("The sky looks so high and my mood is good, but my body is dragging a little.",
     ["dragging", "a", "little."], "하늘은 높고 기분은 좋은데, 몸은 조금 가라앉는다."),
    ("Autumn might be gone before I know it, so I'm getting out this weekend.",
     ["gone", "before", "I", "know", "it,"], "가을이 금방 가 버릴지 모르니, 이번 주말엔 나가서 만끽해야겠다."),
]
FONT_END_T = kr(46); FONT_END_EN = inter(44, "SemiBold"); FONT_END_KO = kr(32, True); FONT_FOOT = kr(28, True)
_end_static = None
def end_panel():
    global _end_static
    if _end_static: return _end_static
    pw, ph = 960, 1100
    im = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 56, 40 + pw, 56 + ph), radius=44, fill=(100, 60, 20, 80))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, 40 + pw, 40 + ph), radius=44, fill=WHITE + (255,))
    # notebook rules
    for y in range(330, 40 + ph - 120, 74):
        d.line((90, y, 40 + pw - 50, y), fill=(232, 216, 196, 255), width=2)
    d.line((130, 300, 130, 40 + ph - 110), fill=(240, 170, 140, 255), width=3)
    title = "오늘 일기, 이 두 줄만 따라 써 보세요"
    tt = tw(FONT_END_T, title)
    lf = leaf_sprite(LEAVES[0], 58)
    tx = 40 + (pw - tt - 70) / 2
    im.alpha_composite(lf, (int(tx + tt + 14), 104))
    d.text((tx, 100), title, font=FONT_END_T, fill=INK)
    d.rounded_rectangle((40 + pw / 2 - 60, 196, 40 + pw / 2 + 60, 204), radius=4, fill=MARK + (255,))
    foot = "#지나쌤영어  #영어공부하자"
    d.text((40 + (pw - tw(FONT_FOOT, foot)) / 2, 40 + ph - 80), foot, font=FONT_FOOT, fill=INK_SOFT)
    _end_static = im
    return im

def draw_end_line(panel_img, k, prog):
    en, marks, ko = END_LINES[k]
    d = ImageDraw.Draw(panel_img)
    font = FONT_END_EN; lh = 74
    words = en.split()
    lines = layout_words(words, font, 790, lh)
    y0 = 330 - 58 + k * 370
    asc, desc = font.getmetrics()
    lay = Image.new("RGBA", panel_img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    mi = None
    for i in range(len(words)):
        if words[i:i + len(marks)] == marks: mi = set(range(i, i + len(marks)))
    for li, line in enumerate(lines):
        y = y0 + li * lh
        for (j, x, wl) in line:
            if j in mi:
                dl.rounded_rectangle((160 + x - 6, y + asc * 0.4, 160 + x + wl + 6, y + asc + desc * 0.5), radius=8, fill=MARK + (255,))
        for (j, x, wl) in line:
            dl.text((160 + x, y), words[j], font=font, fill=INK)
    yk = y0 + len(lines) * lh + 4
    kl = [ko] if tw(FONT_END_KO, ko) < 790 else [ko[:ko.index(", ") + 1], ko[ko.index(", ") + 2:]]
    for q, l in enumerate(kl):
        dl.text((160, yk + q * 46), l, font=FONT_END_KO, fill=INK_SOFT)
    # handwriting-like wipe reveal
    m = Image.new("L", lay.size, 0)
    xr = 120 + prog * 860
    ImageDraw.Draw(m).rectangle((0, 0, xr, lay.height), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(18))
    a = Image.fromarray((np.array(lay.getchannel("A")).astype(np.float32) * np.array(m) / 255).astype(np.uint8))
    lay.putalpha(a)
    panel_img.alpha_composite(lay)

# ---------- scene state ----------
def active(t):
    """returns list of (sentence, unit, alpha, yoff) to draw"""
    out = []
    flat = []
    for s in SENTS:
        for u in s["units"]: flat.append((s, u))
    for k, (s, u) in enumerate(flat):
        show_from = 0 if k == 0 else u["s"] - 0.18
        nxt = flat[k + 1][1]["s"] - 0.18 if k + 1 < len(flat) else END_T0
        if show_from <= t < nxt + 0.16:
            a = 1.0; yoff = 0
            if k > 0 and t < show_from + 0.28:
                p = ease_out((t - show_from) / 0.28); a = p; yoff = 26 * (1 - p)
            if t >= nxt:
                p = (t - nxt) / 0.16; a *= 1 - p; yoff -= 10 * p
            out.append((s, u, a, yoff))
    return out

def korean_state(t):
    out = []
    for k, s in enumerate(SENTS):
        a0 = 0 if k == 0 else s["s"] - 0.18
        a1 = SENTS[k + 1]["s"] - 0.18 if k + 1 < len(SENTS) else END_T0
        if a0 <= t < a1 + 0.16:
            a = 1.0
            if k > 0 and t < a0 + 0.25: a = ease_out((t - a0) / 0.25)
            if t >= a1: a *= 1 - (t - a1) / 0.16
            out.append((s["ko"], a))
    return out

def card_windows():
    wins = []
    for k, s in enumerate(SENTS):
        nxt_s = SENTS[k + 1]["s"] - 0.2 if k + 1 < len(SENTS) else END_T0 - 0.1
        for j, c in enumerate(s["cards"]):
            end = s["cards"][j + 1]["t"] - 0.2 if j + 1 < len(s["cards"]) else nxt_s
            wins.append((c, end))
    return wins
CARDWIN = card_windows()

def render_main(t):
    img = BGIMG.copy()
    endp = clamp((t - END_T0) / 0.5)
    draw_leaves(img, t)
    e = env_at(t)
    mouth = -10 + 19 * min(1, e)
    im, x, y, sway = char_layer(t, mouth, hop_at(t))
    # bulb position after transform (approx; ignore rotation offset)
    bx = x + im.width / 2 + (BULB[0] - CHAR0.shape[1] / 2) * CS
    by = y + im.height - (CHAR0.shape[0] - BULB[1]) * CS
    bulb_glow(img, t, bx, by)
    img.alpha_composite(im, (x, y))
    draw_label(img)
    for s, u, a, yoff in active(t): draw_sentence(img, s, u, t, a, yoff)
    for c, end in CARDWIN: draw_card(img, c, t, end)
    for ko, a in korean_state(t): draw_korean(img, ko, a)
    if endp > 0:
        dim = Image.new("RGBA", (W, H), BG + (int(150 * ease_out(endp)),))
        img.alpha_composite(dim)
        p = end_panel().copy()
        p1 = clamp((t - (END_T0 + 0.45)) / 1.3); p2 = clamp((t - (END_T0 + 1.9)) / 1.3)
        if p1 > 0: draw_end_line(p, 0, ease_in_out(p1))
        if p2 > 0: draw_end_line(p, 1, ease_in_out(p2))
        yy = 330 + 120 * (1 - ease_out(endp / 1.0))
        if endp < 1: p.putalpha(p.getchannel("A").point(lambda v: int(v * ease_out(endp))))
        img.alpha_composite(p, (int((W - p.width) / 2), int(yy)))
    return img

FRAME0 = None
def frame(t):
    global FRAME0
    if t >= LOOP_T0:
        if FRAME0 is None: FRAME0 = render_main(0.0)
        k = ease_in_out((t - LOOP_T0) / (DUR - 1 / FPS - LOOP_T0))
        return Image.blend(render_main(min(t, LOOP_T0)).convert("RGB"), FRAME0.convert("RGB"), k)
    return render_main(t).convert("RGB")

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "sheet":
        ts = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [i for i in range(0, 36)]
        thumbs = [frame(t).resize((270, 480), Image.LANCZOS) for t in ts]
        cols = 6; rows = math.ceil(len(thumbs) / cols)
        sheet = Image.new("RGB", (cols * 270, rows * 500), (30, 30, 30)); dd = ImageDraw.Draw(sheet)
        for i, th in enumerate(thumbs):
            sheet.paste(th, ((i % cols) * 270, (i // cols) * 500 + 20))
            dd.text(((i % cols) * 270 + 6, (i // cols) * 500 + 2), f"{ts[i]:.1f}s", fill=(255, 255, 255))
        sheet.save(ROOT + "sheet.jpg", quality=85)
    elif mode == "still":
        frame(float(sys.argv[2])).save(ROOT + f"still_{sys.argv[2]}.jpg", quality=90)
    elif mode == "video":
        n = int(DUR * FPS)
        p = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                              "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", ROOT + "mix.wav",
                              "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                              "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                              ROOT + "out.mp4"], stdin=subprocess.PIPE)
        for i in range(n):
            p.stdin.write(frame(i / FPS).tobytes())
            if i % 150 == 0: print(i, flush=True)
        p.stdin.close(); p.wait(); print("done")
