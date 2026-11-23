import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
"""Character-free, emoji-rich version of the autumn diary reel."""
import math, sys, subprocess, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, _HERE)
import render as R
from render import (LAV, ROSE, W, H, FPS, DUR, ROOT, BG, INK, INK_SOFT, MARK, CARD, SUN, WHITE,
                    inter, kr, clamp, ease_out, ease_in_out, pop, env_at, tw, layout_words,
                    SENTS, CARDWIN, END_LINES, FONT_END_T, FONT_END_EN, FONT_END_KO, FONT_FOOT)

# ---------------- emoji ----------------
EF = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
_ecache = {}
def emoji(ch, size):
    k = (ch, size)
    if k in _ecache: return _ecache[k]
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=EF, embedded_color=True)
    im = im.crop(im.getbbox())
    s = size / max(im.size)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    _ecache[k] = im
    return im

EMO_RE = re.compile(r"([☀-➿\U0001F000-\U0001FAFF]️?)")
def draw_mixed(img, xy, text, font, fill, esize=None, measure=False):
    """draw text where emoji segments use the colour-emoji font; returns width"""
    esize = esize or int(font.size * 1.05)
    parts = [p for p in EMO_RE.split(text) if p]
    x, y = xy; asc, _ = font.getmetrics()
    d = None if measure else ImageDraw.Draw(img)
    for p in parts:
        if EMO_RE.fullmatch(p):
            if not measure:
                e = emoji(p, esize)
                img.alpha_composite(e, (int(x), int(y + asc - e.height + esize * 0.12)))
            x += esize + 6
        else:
            if not measure: d.text((x, y), p, font=font, fill=fill)
            x += tw(font, p)
    return x - xy[0]
def mixed_w(text, font, esize=None): return draw_mixed(None, (0, 0), text, font, None, esize, True)

# ---------------- per-scene emoji ----------------
# one sticker pair per display unit (sentence id, unit index)
STICKERS = {}
from exprs import KO_EMO, CARD_EMO, EXPRS

def split_emo(s): return [p for p in EMO_RE.split(s) if p and EMO_RE.fullmatch(p)]

# ---------------- background ----------------
def make_bg():
    im = Image.new("RGB", (W, H), BG)
    rng = np.random.default_rng(3)
    arr = np.clip(np.array(im).astype(np.int16) + rng.normal(0, 4, (H, W, 1)).astype(np.int16), 0, 255).astype(np.uint8)
    im = Image.fromarray(arr)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((90, 420, 990, 1320), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    im.paste(Image.new("RGB", (W, H), SUN), (0, 0), glow.point(lambda v: int(v * 0.7)))
    return im.convert("RGBA")
BGIMG = make_bg()

FALL = [("🩹", 44, 110, 0.00, 2), ("💭", 50, 930, 0.30, 3), ("🍃", 44, 300, 0.55, 2), ("✨", 46, 800, 0.75, 4),
        ("💭", 38, 60, 0.42, 3), ("🩹", 44, 1010, 0.12, 2), ("🍃", 36, 560, 0.88, 3), ("✨", 38, 690, 0.20, 2)]
def draw_falling(img, t, alpha=0.6):
    span = H + 240
    for ch, sz, x0, ph, m in FALL:
        prog = (t / DUR + ph) % 1.0
        y = -120 + prog * span
        x = x0 + 45 * math.sin(2 * math.pi * (t / DUR * m + ph * 3))
        ang = 40 * math.sin(2 * math.pi * (t / DUR * (m + 1) + ph))
        e = emoji(ch, sz).rotate(ang, resample=Image.BICUBIC, expand=True)
        e = e.copy(); e.putalpha(e.getchannel("A").point(lambda v: int(v * alpha)))
        img.alpha_composite(e, (int(x - e.width / 2), int(y - e.height / 2)))

# ---------------- top: label + progress ----------------
FL = inter(28, "Bold"); FLK = kr(28)
def draw_top(img, t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a, b = "MY ENGLISH DIARY", "  ·  가을 편"
    wa, wb = tw(FL, a), tw(FLK, b)
    total = 44 + wa + wb
    x0 = (W - total) / 2 - 26
    d.rounded_rectangle((x0, 166, x0 + total + 52, 220), radius=27, fill=WHITE + (230,), outline=INK + (200,), width=3)
    img.alpha_composite(lay)
    img.alpha_composite(emoji("🍂", 36), (int(x0 + 22), 174))
    d = ImageDraw.Draw(img)
    d.text((x0 + 70, 176), a, font=FL, fill=INK)
    d.text((x0 + 70 + wa, 171), b, font=FLK, fill=INK)
    # progress dots
    cur = 0
    for k, s in enumerate(SENTS):
        if t >= s["s"] - 0.2: cur = k
    if t >= R.END_T0: cur = len(SENTS)
    n = len(SENTS); gap = 34; dx0 = W / 2 - (n - 1) * gap / 2
    for k in range(n):
        x = dx0 + k * gap
        if k < cur: d.ellipse((x - 7, 258, x + 7, 272), fill=MARK)
        elif k == cur: d.rounded_rectangle((x - 13, 258, x + 13, 272), radius=7, fill=INK)
        else: d.ellipse((x - 7, 258, x + 7, 272), outline=INK_SOFT, width=2)

# ---------------- sticker (replaces the character) ----------------
def unit_list():
    out = []
    for s in SENTS:
        for ui, u in enumerate(s["units"]): out.append((s, ui, u))
    return out
UNITS = unit_list()

def draw_sticker(img, t):
    if t >= R.END_T0 + 0.3: return
    for k, (s, ui, u) in enumerate(UNITS):
        a0 = 0 if k == 0 else u["s"] - 0.18
        a1 = UNITS[k + 1][2]["s"] - 0.18 if k + 1 < len(UNITS) else R.END_T0
        if not (a0 <= t < a1 + 0.16): continue
        emos = split_emo(STICKERS[(s["id"], ui)])
        p_in = 1.0 if k == 0 else (t - a0) / 0.42
        al = ease_out(p_in / 0.5)
        if t >= a1: al *= 1 - (t - a1) / 0.16
        e = env_at(t)
        for j, ch in enumerate(emos):
            pj = clamp(p_in - j * 0.25)
            sc = 0.6 + 0.4 * pop(pj) if pj < 1 else 1.0
            size = int((230 if j == 0 else 150) * sc * (1 + 0.05 * e * (1 if j == 0 else 0)))
            bob = 12 * math.sin(2 * math.pi * (t / 3.0 + j * 0.35))
            ang = (6 if j == 0 else -10) * math.sin(2 * math.pi * (t / 6.0 + j * 0.2)) + (0 if j == 0 else 12)
            im = emoji(ch, max(1, size)).rotate(ang, resample=Image.BICUBIC, expand=True)
            if al < 1:
                im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * clamp(al))))
            cx, cy = (500, 520) if j == 0 else (670, 450)
            img.alpha_composite(im, (int(cx - im.width / 2), int(cy + bob - im.height / 2)))

# ---------------- voice bars (speaking indicator) ----------------
def draw_bars(img, t, alpha=1.0):
    d = ImageDraw.Draw(img)
    e = env_at(t); n = 13
    for i in range(n):
        x = W / 2 + (i - (n - 1) / 2) * 22
        hh = 8 + 46 * e * (0.45 + 0.55 * abs(math.sin(t * 9 + i * 1.7))) * (1 - abs(i - 6) / 9)
        col = LAV if abs(i - 6) < 3 else INK_SOFT
        d.rounded_rectangle((x - 5, 700 - hh / 2, x + 5, 700 + hh / 2), radius=5, fill=col + (int(255 * alpha),))

# ---------------- sentence ----------------
FONT_EN = inter(70); FONT_EN_BIG = inter(118, "Bold")
def draw_sentence(img, s, unit, t, alpha, yoff):
    words = [s["words"][i]["w"] for i in unit["idx"]]
    font = FONT_EN_BIG if s["big"] else FONT_EN
    lh = int(font.size * (1.15 if s["big"] else 1.3))
    lines = layout_words(words, font, 960, lh)
    asc, desc = font.getmetrics()
    top = 905 - len(lines) * lh / 2 + yoff
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cw = set()
    for c in s["cards"]: cw.update(range(c["i0"], c["i1"] + 1))
    for m0, m1 in s.get("marks", []): cw.update(range(m0, m1 + 1))
    for li, line in enumerate(lines):
        lw = line[-1][1] + line[-1][2]; x0 = (W - lw) / 2; y = top + li * lh
        for (j, x, wl) in line:
            gi = unit["idx"][j]; wd = s["words"][gi]
            mk = 1 if (gi in cw and t >= wd["s"]) else (ease_out((t - wd["s"]) / 0.10) if wd["s"] <= t < wd["e"] + 0.04 else 0)
            if mk > 0:
                d.rounded_rectangle((x0 + x - 9, y + asc * 0.36, x0 + x - 9 + (wl + 18) * mk, y + asc + desc * 0.55),
                                    radius=12, fill=MARK + (int(235 * alpha),))
        for (j, x, wl) in line:
            wd = s["words"][unit["idx"][j]]
            d.text((x0 + x, y), wd["w"], font=font, fill=INK + (int(255 * (1 if t >= wd["s"] else 0.34) * alpha),))
    img.alpha_composite(lay)

# ---------------- korean ----------------
FONT_KO = kr(42)
def draw_korean(img, s, alpha):
    lines = s["ko"].split("\n"); lines[-1] += KO_EMO[s["id"]]
    lh = 60; widths = [mixed_w(l, FONT_KO, 46) for l in lines]
    bw = max(widths) + 84; bh = len(lines) * lh + 44
    cy = 1585; x0 = (W - bw) / 2; y0 = cy - bh / 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10, x0 + bw, y0 + bh + 10), radius=30, fill=(90, 60, 30, int(45 * alpha)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=30, fill=WHITE + (250,))
    for i, l in enumerate(lines):
        draw_mixed(lay, ((W - widths[i]) / 2, y0 + 18 + i * lh), l, FONT_KO, INK, 46)
    if alpha < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(lay)

def korean_state(t):
    out = []
    for k, s in enumerate(SENTS):
        a0 = 0 if k == 0 else s["s"] - 0.18
        a1 = SENTS[k + 1]["s"] - 0.18 if k + 1 < len(SENTS) else R.END_T0
        if a0 <= t < a1 + 0.16:
            a = 1.0
            if k > 0 and t < a0 + 0.25: a = ease_out((t - a0) / 0.25)
            if t >= a1: a *= 1 - (t - a1) / 0.16
            out.append((s, a))
    return out

# ---------------- card ----------------
FCE = inter(54, "Bold"); FCK = kr(40); FCT = kr(26, True)
_cc = {}
def card_sprite(en, ko):
    if (en, ko) in _cc: return _cc[(en, ko)]
    tag = "오늘의 표현"
    fce = FCE if tw(FCE, en) <= 680 else inter(int(54 * 680 / tw(FCE, en)), "Bold")
    w = int(max(tw(fce, en), tw(FCK, ko), 320) + 100); h = 222
    im = Image.new("RGBA", (w + 120, h + 110), (0, 0, 0, 0))
    ox, oy = 60, 55
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((ox, oy + 12, ox + w, oy + h + 12), radius=36, fill=(80, 70, 110, 60))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((ox, oy, ox + w, oy + h), radius=36, fill=CARD + (255,))
    tg = tw(FCT, tag)
    d.rounded_rectangle((ox + (w - tg) / 2 - 20, oy + 18, ox + (w + tg) / 2 + 20, oy + 62), radius=22, fill=WHITE + (255,))
    d.text((ox + (w - tg) / 2, oy + 21), tag, font=FCT, fill=INK)
    d.text((ox + (w - tw(fce, en)) / 2, oy + 74 + (54 - fce.size) * 0.6), en, font=fce, fill=INK)
    d.text((ox + (w - tw(FCK, ko)) / 2, oy + 142), ko, font=FCK, fill=INK)
    e = emoji(CARD_EMO[en], 104).rotate(-14, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(e, (int(ox + w - e.width * 0.62), int(oy - e.height * 0.42)))
    e2 = emoji("✨", 54)
    im.alpha_composite(e2, (int(ox - 24), int(oy + h - 40)))
    _cc[(en, ko)] = im
    return im

def draw_card(img, c, t, t_end):
    d_in = t - c["t"]
    if d_in < 0 or t > t_end + 0.2: return
    sc = 0.82 + 0.18 * pop(d_in / 0.34); al = ease_out(d_in / 0.18)
    if t > t_end:
        k = (t - t_end) / 0.2; al *= 1 - ease_out(k); sc *= 1 - 0.05 * k
    spr = card_sprite(c["en"], c["ko"])
    s = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BICUBIC)
    s = s.rotate(-2.2 * (1 - ease_out(d_in / 0.5)) - 1.0, resample=Image.BICUBIC, expand=True)
    if al < 1: s.putalpha(s.getchannel("A").point(lambda v: int(v * al)))
    img.alpha_composite(s, (int(585 - s.width / 2), int(1250 - s.height / 2)))

# ---------------- ending ----------------
_endp = None
def end_panel():
    global _endp
    if _endp: return _endp
    pw, ph = 960, 1140
    im = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 56, 40 + pw, 56 + ph), radius=44, fill=(100, 60, 20, 80))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, 40 + pw, 40 + ph), radius=44, fill=WHITE + (255,))
    for y in range(330, 40 + ph - 120, 74): d.line((90, y, 40 + pw - 50, y), fill=(232, 216, 196, 255), width=2)
    d.line((130, 300, 130, 40 + ph - 110), fill=(240, 170, 140, 255), width=3)
    title = "오늘 일기, 이 두 줄만 따라 써 보세요 ✍️"
    tw_ = mixed_w(title, FONT_END_T, 52)
    draw_mixed(im, (40 + (pw - tw_) / 2, 100), title, FONT_END_T, INK, 52)
    d.rounded_rectangle((40 + pw / 2 - 60, 196, 40 + pw / 2 + 60, 204), radius=4, fill=MARK + (255,))
    foot = "📌 저장해 두고 하루 한 줄씩  #지나쌤영어"
    fw = mixed_w(foot, FONT_FOOT, 30)
    draw_mixed(im, (40 + (pw - fw) / 2, 40 + ph - 82), foot, FONT_FOOT, INK_SOFT, 30)
    for ch, x, y, sz, a in [("🍂", 14, ph - 30, 96, -18), ("🍁", 920, ph - 40, 88, 16), ("📝", 930, -6, 84, 10)]:
        im.alpha_composite(emoji(ch, sz).rotate(a, resample=Image.BICUBIC, expand=True), (x, y))
    _endp = im
    return im

END_EMO = ["🐌", "⏳"]
def draw_end_line(panel, k, prog):
    en, marks, ko = END_LINES[k]
    font = FONT_END_EN; lh = 74; words = en.split()
    lines = layout_words(words, font, 790, lh)
    y0 = 330 - 58 + k * 380; asc, desc = font.getmetrics()
    lay = Image.new("RGBA", panel.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    mi = set()
    for i in range(len(words)):
        if words[i:i + len(marks)] == marks: mi = set(range(i, i + len(marks)))
    for li, line in enumerate(lines):
        y = y0 + li * lh
        for (j, x, wl) in line:
            if j in mi: dl.rounded_rectangle((160 + x - 6, y + asc * 0.4, 160 + x + wl + 6, y + asc + desc * 0.5), radius=8, fill=MARK + (255,))
        for (j, x, wl) in line: dl.text((160 + x, y), words[j], font=font, fill=INK)
    last = lines[-1][-1]
    lay.alpha_composite(emoji(END_EMO[k], 52), (int(160 + last[1] + last[2] + 12), int(y0 + (len(lines) - 1) * lh + 2)))
    yk = y0 + len(lines) * lh + 4
    kl = [ko] if tw(FONT_END_KO, ko) < 790 else [ko[:ko.index(", ") + 1], ko[ko.index(", ") + 2:]]
    for q, l in enumerate(kl): dl.text((160, yk + q * 46), l, font=FONT_END_KO, fill=INK_SOFT)
    m = Image.new("L", lay.size, 0)
    ImageDraw.Draw(m).rectangle((0, 0, 120 + prog * 900, lay.height), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(18))
    lay.putalpha(Image.fromarray((np.array(lay.getchannel("A")).astype(np.float32) * np.array(m) / 255).astype(np.uint8)))
    panel.alpha_composite(lay)

# ---------------- compose ----------------
def render_main(t):
    img = BGIMG.copy()
    draw_falling(img, t)
    endp = clamp((t - R.END_T0) / 0.5)
    draw_sticker(img, t)
    draw_bars(img, t, 1 - endp)
    draw_top(img, t)
    for s, u, a, yoff in R.active(t): draw_sentence(img, s, u, t, a, yoff)
    for c, end in CARDWIN: draw_card(img, c, t, end)
    import pile
    pile.draw_pile(img, t, emoji, 1 - endp)
    for s, a in korean_state(t): draw_korean(img, s, a)
    if endp > 0:
        img.alpha_composite(Image.new("RGBA", (W, H), BG + (int(150 * ease_out(endp)),)))
        p = end_panel().copy()
        p1 = clamp((t - (R.END_T0 + 0.45)) / 1.3); p2 = clamp((t - (R.END_T0 + 1.9)) / 1.3)
        if p1 > 0: draw_end_line(p, 0, ease_in_out(p1))
        if p2 > 0: draw_end_line(p, 1, ease_in_out(p2))
        yy = 330 + 120 * (1 - ease_out(endp))
        if endp < 1: p.putalpha(p.getchannel("A").point(lambda v: int(v * ease_out(endp))))
        img.alpha_composite(p, (int((W - p.width) / 2), int(yy)))
    return img

FRAME0 = None
def frame(t):
    global FRAME0
    if t >= R.LOOP_T0:
        if FRAME0 is None: FRAME0 = render_main(0.0).convert("RGB")
        k = ease_in_out((t - R.LOOP_T0) / (DUR - 1 / FPS - R.LOOP_T0))
        return Image.blend(render_main(R.LOOP_T0).convert("RGB"), FRAME0, k)
    return render_main(t).convert("RGB")

# ---------------- v4 overrides: handwritten title, brand tagline, "오늘 써볼 표현" ending ----------------
FHAND = ImageFont.truetype("/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrechorus-mediumitalic.otf", 104)
FTAG = kr(30, True)
TAGLINE = "읽고 따라 쓰면 내 것이 돼요 ✍️"
_top_static = None
def top_static():
    global _top_static
    if _top_static: return _top_static
    lay = Image.new("RGBA", (W, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    title = "My English Diary"
    w = tw(FHAND, title); x0 = (W - w) / 2
    # brush underline in highlight colour
    for k in range(5):
        d.line((x0 + 30 + k, 262 - k * 0.6 + 2, x0 + w - 10, 250 + k), fill=ROSE + (255,), width=8)
    d.text((x0, 136), title, font=FHAND, fill=INK)
    tw_ = mixed_w(TAGLINE, FTAG, 34)
    draw_mixed(lay, ((W - tw_) / 2, 284), TAGLINE, FTAG, INK_SOFT, 34)
    _top_static = lay
    return lay

def draw_top(img, t, alpha=1.0):
    lay = top_static()
    if alpha < 1:
        lay = lay.copy(); lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    cur = 0
    for k, s in enumerate(SENTS):
        if t >= s["s"] - 0.2: cur = k
    n = len(SENTS); gap = 34; dx0 = W / 2 - (n - 1) * gap / 2; y = 352
    a = int(255 * alpha)
    for k in range(n):
        x = dx0 + k * gap
        if k < cur: d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=LAV + (a,))
        elif k == cur: d.rounded_rectangle((x - 13, y - 7, x + 13, y + 7), radius=7, fill=INK + (a,))
        else: d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=INK_SOFT + (a,), width=2)

FX_EN = inter(46, "Bold"); FX_KO = kr(32, True); FX_T = kr(54); FX_N = inter(26, "Bold"); FX_F = kr(28, True)
PX, PY, PW, PH = 60, 250, 960, 1360
ROW0, ROWH = 450, 150
_ep = None
def end_panel():
    global _ep
    if _ep: return _ep
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((PX, PY + 16, PX + PW, PY + PH + 16), radius=48, fill=(100, 60, 20, 80))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((PX, PY, PX + PW, PY + PH), radius=48, fill=WHITE + (255,))
    title = "오늘 써볼 표현 ✍️"
    tw_ = mixed_w(title, FX_T, 60)
    # highlight swipe behind title
    d.rounded_rectangle((W / 2 - tw_ / 2 - 14, PY + 98, W / 2 + tw_ / 2 + 14, PY + 140), radius=14, fill=MARK + (255,))
    draw_mixed(im, ((W - tw_) / 2, PY + 64), title, FX_T, INK, 60)
    foot = "📌 저장해 두고 하나씩 써 보세요"
    fw = mixed_w(foot, FX_F, 30)
    draw_mixed(im, ((W - fw) / 2, PY + PH - 78), foot, FX_F, INK_SOFT, 30)
    for ch, x, y, sz, a in [("💡", PX - 30, PY - 40, 100, -8), ("🌱", PX + PW - 70, PY + PH - 70, 88, 12)]:
        im.alpha_composite(emoji(ch, sz).rotate(a, resample=Image.BICUBIC, expand=True), (x, y))
    _ep = im
    return im

_rows = {}
def row_sprite(k):
    if k in _rows: return _rows[k]
    em, en, ko = EXPRS[k]
    im = Image.new("RGBA", (PW, ROWH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((48, 30, 96, 78), fill=INK)
    n = str(k + 1); d.text((72 - tw(FX_N, n) / 2, 38), n, font=FX_N, fill=WHITE)
    fx = FX_EN if tw(FX_EN, en) <= 620 else inter(int(46 * 620 / tw(FX_EN, en)), "Bold")
    asc, desc = fx.getmetrics(); x = 124; y = 22 + (46 - fx.size) * 0.5
    wl = tw(fx, en)
    d.rounded_rectangle((x - 10, y + asc * 0.38, x + wl + 10, y + asc + desc * 0.55), radius=12, fill=MARK + (255,))
    d.text((x, y), en, font=fx, fill=INK)
    d.text((x, y + 70), ko, font=FX_KO, fill=INK_SOFT)
    e = emoji(em, 72); im.alpha_composite(e, (PW - 60 - e.width, int((ROWH - e.height) / 2) - 8))
    if k < len(EXPRS) - 1: d.line((48, ROWH - 4, PW - 48, ROWH - 4), fill=(236, 222, 204, 255), width=2)
    _rows[k] = im
    return im

def draw_end(img, t, endp):
    img.alpha_composite(Image.new("RGBA", (W, H), BG + (int(170 * ease_out(endp)),)))
    p = end_panel().copy()
    for k in range(len(EXPRS)):
        tk = t - (R.END_T0 + 0.45 + k * 0.28)
        if tk <= 0: continue
        r = row_sprite(k)
        sc = 0.9 + 0.1 * pop(tk / 0.35); al = ease_out(tk / 0.2)
        rr = r.resize((int(r.width * sc), int(r.height * sc)), Image.BICUBIC)
        if al < 1: rr.putalpha(rr.getchannel("A").point(lambda v: int(v * al)))
        p.alpha_composite(rr, (int(PX + (PW - rr.width) / 2), int(ROW0 + k * ROWH + (ROWH - rr.height) / 2 + 20 * (1 - al))))
    dy = 120 * (1 - ease_out(endp))
    if endp < 1: p.putalpha(p.getchannel("A").point(lambda v: int(v * ease_out(endp))))
    img.alpha_composite(p, (0, int(dy)))

def render_main(t):
    img = BGIMG.copy()
    draw_falling(img, t)
    endp = clamp((t - R.END_T0) / 0.5)
    draw_sticker(img, t)
    draw_bars(img, t, 1 - endp)
    draw_top(img, t, 1 - endp)
    for s, u, a, yoff in R.active(t): draw_sentence(img, s, u, t, a, yoff)
    for c, end in CARDWIN: draw_card(img, c, t, end)
    import pile
    pile.draw_pile(img, t, emoji, 1 - endp)
    for s, a in korean_state(t): draw_korean(img, s, a)
    if endp > 0: draw_end(img, t, endp)
    return img


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "sheet":
        ts = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(range(36))
        th = [frame(t).resize((270, 480), Image.LANCZOS) for t in ts]
        cols = 6; rows = math.ceil(len(th) / cols)
        sheet = Image.new("RGB", (cols * 270, rows * 500), (30, 30, 30)); dd = ImageDraw.Draw(sheet)
        for i, im in enumerate(th):
            sheet.paste(im, ((i % cols) * 270, (i // cols) * 500 + 20)); dd.text(((i % cols) * 270 + 6, (i // cols) * 500 + 2), f"{ts[i]:.1f}s", fill=(255, 255, 255))
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
        p.stdin.close(); p.wait(); print("done")
