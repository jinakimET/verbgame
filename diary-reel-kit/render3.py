import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
"""Photo layout: title → frameless horizontal photo → sentence → Korean.
Expression card pops in the middle of the photo, then flies into the counter."""
import math, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, _HERE)
import render as R
import render2 as V
from render import (W, H, FPS, DUR, ROOT, BG, INK, INK_SOFT, MARK, WHITE, inter, kr, clamp,
                    ease_out, ease_in_out, pop, tw, layout_words, SENTS)

# ---------------- photos ----------------
# sentence id -> (file, focal x, focal y)
from episode_cfg import PHOTOS, COUNTER_EMO, BURST
PY0, PW, PH = 388, 1080, 600
ZMAX = 1.07
_ph = {}
def photo_base(key):
    """cover-crop around the focal point at ZMAX resolution"""
    if key in _ph: return _ph[key]
    f, fx, fy = key
    im = Image.open(ROOT + "photos/" + f).convert("RGB")
    tw_, th_ = int(PW * ZMAX), int(PH * ZMAX)
    s = max(tw_ / im.width, th_ / im.height)
    im = im.resize((int(im.width * s + 0.5), int(im.height * s + 0.5)), Image.LANCZOS)
    cx = clamp(fx * im.width - tw_ / 2, 0, im.width - tw_); cy = clamp(fy * im.height - th_ / 2, 0, im.height - th_)
    im = im.crop((int(cx), int(cy), int(cx) + tw_, int(cy) + th_))
    _ph[key] = im
    return im

def photo_frame(sid, z):
    """z in [0,1]: slow push-in"""
    b = photo_base(sid)
    sc = 1 / ZMAX * (1 + (ZMAX - 1) * z)          # visible fraction grows smaller as we zoom
    w, h = b.width / ZMAX / (1 + (ZMAX - 1) * z) * 1.0, b.height / ZMAX / (1 + (ZMAX - 1) * z)
    x0, y0 = (b.width - w) / 2, (b.height - h) / 2
    return b.resize((PW, PH), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))

def sentence_windows():
    out = []
    for k, s in enumerate(SENTS):
        a0 = 0 if k == 0 else s["s"] - 0.18
        a1 = SENTS[k + 1]["s"] - 0.18 if k + 1 < len(SENTS) else R.END_T0
        out.append((s, a0, a1))
    return out
SWIN = sentence_windows()

def photo_windows():
    flat = [(s, ui, u) for s in SENTS for ui, u in enumerate(s["units"])]
    wins = []
    for k, (s, ui, u) in enumerate(flat):
        key = PHOTOS.get((s["id"], ui), PHOTOS.get(s["id"]))
        a0 = 0 if k == 0 else u["s"] - 0.18
        if wins and wins[-1][0] == key: continue
        if wins: wins[-1][2] = a0
        wins.append([key, a0, R.END_T0])
    return wins
PWIN = photo_windows()

def draw_photo(img, t):
    for k, (key, a0, a1) in enumerate(PWIN):
        if not (a0 <= t < a1 + 0.45): continue
        z = clamp((t - a0) / max(1, (a1 - a0) + 0.45))
        fr = photo_frame(key, z).convert("RGBA")
        al = 1.0
        if k > 0 and t < a0 + 0.45: al = ease_in_out((t - a0) / 0.45)
        if al < 1: fr.putalpha(int(255 * al))
        img.alpha_composite(fr, (0, PY0))

# ---------------- sentence (middle) ----------------
FONT_EN = inter(64); FONT_EN_BIG = inter(104, "Bold")
SCY = 1192
def draw_sentence(img, s, unit, t, alpha, yoff):
    words = [s["words"][i]["w"] for i in unit["idx"]]
    font = FONT_EN_BIG if s["big"] else FONT_EN
    lh = int(font.size * (1.15 if s["big"] else 1.3))
    lines = layout_words(words, font, 980, lh)
    asc, desc = font.getmetrics()
    top = SCY - len(lines) * lh / 2 + yoff
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

# ---------------- korean (below) ----------------
FONT_KO = kr(40)
def draw_korean(img, s, alpha):
    lines = s["ko"].split("\n"); lines[-1] += V.KO_EMO[s["id"]]
    lh = 56; widths = [V.mixed_w(l, FONT_KO, 44) for l in lines]
    bw = max(widths) + 80; bh = len(lines) * lh + 40
    top = 1425; x0 = (W - bw) / 2; y0 = top
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10, x0 + bw, y0 + bh + 10), radius=28, fill=(90, 60, 30, int(40 * alpha)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=28, fill=WHITE + (250,))
    for i, l in enumerate(lines):
        V.draw_mixed(lay, ((W - widths[i]) / 2, y0 + 16 + i * lh), l, FONT_KO, INK, 44)
    if alpha < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(lay)

# ---------------- card on photo → flies into counter ----------------
CARD_C = (540, PY0 + PH / 2)
CNT_C = (905, PY0 + PH - 52)
def card_windows():
    allc = [c for s in SENTS for c in s["cards"]]
    out = []
    for i, c in enumerate(allc):
        s = next(s for s in SENTS if c in s["cards"])
        sw = next(a1 for (ss, a0, a1) in SWIN if ss is s)
        end = c["t"] + 2.6
        if i + 1 < len(allc): end = min(end, allc[i + 1]["t"] - 0.5)
        end = min(end, sw + 0.5, R.END_T0 - 0.6)
        out.append((c, end, end + 0.45))       # (card, start flying, arrive)
    return out
CW = card_windows()
ARRIVALS = [a for _, _, a in CW]

def draw_card(img, c, t, t_fly, t_arr):
    d_in = t - c["t"]
    if d_in < 0 or t >= t_arr: return
    spr = V.card_sprite(c["en"], c["ko"])
    if t < t_fly:
        sc = 0.82 + 0.18 * pop(d_in / 0.34); al = ease_out(d_in / 0.18)
        x, y = CARD_C; ang = -2.2 * (1 - ease_out(d_in / 0.5)) - 1.0
    else:
        p = (t - t_fly) / (t_arr - t_fly); q = ease_in_out(p)
        sc = 1 - 0.88 * q; al = 1 - 0.3 * q
        x = CARD_C[0] + (CNT_C[0] - CARD_C[0]) * q
        y = CARD_C[1] + (CNT_C[1] - CARD_C[1]) * q - 120 * math.sin(math.pi * p)
        ang = -1 - 25 * q
    s = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BICUBIC)
    s = s.rotate(ang, resample=Image.BICUBIC, expand=True)
    if al < 1: s.putalpha(s.getchannel("A").point(lambda v: int(v * al)))
    img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))

FCNT = kr(28)
def draw_counter(img, t, fade):
    if fade <= 0: return
    got = sum(1 for a in ARRIVALS if t >= a)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bump = 0
    for a in ARRIVALS:
        d = t - a
        if 0 <= d < 0.5: bump = 0.22 * math.exp(-d * 8)
    label = f"모은 표현 {got}/{len(ARRIVALS)}"
    w = tw(FCNT, label) + 92; hgt = 58
    sc = 1 + bump
    x0 = CNT_C[0] - w * sc / 2; y0 = CNT_C[1] - hgt * sc / 2
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x0, y0 + 4, x0 + w * sc, y0 + hgt * sc + 4), radius=int(hgt * sc / 2), fill=(60, 30, 10, 60))
    d.rounded_rectangle((x0, y0, x0 + w * sc, y0 + hgt * sc), radius=int(hgt * sc / 2), fill=WHITE + (245,))
    lay.alpha_composite(V.emoji(COUNTER_EMO, int(36 * sc)), (int(x0 + 16 * sc), int(y0 + 10 * sc)))
    d.text((x0 + 62 * sc, y0 + 11 * sc), label, font=kr(int(28 * sc)), fill=INK)
    # leaf burst on arrival ("뿅뿅")
    for a in ARRIVALS:
        dd = t - a
        if 0 <= dd < 0.8:
            for j, ch in enumerate(BURST):
                ang = -math.pi / 2 + (j - 2) * 0.55
                r = 30 + 150 * ease_out(dd / 0.8)
                ex = CNT_C[0] + math.cos(ang) * r; ey = CNT_C[1] + math.sin(ang) * r + 140 * dd * dd
                e = V.emoji(ch, 40).rotate(dd * 300 + j * 40, resample=Image.BICUBIC, expand=True)
                e = e.copy(); e.putalpha(e.getchannel("A").point(lambda v: int(v * (1 - dd / 0.8))))
                lay.alpha_composite(e, (int(ex - e.width / 2), int(ey - e.height / 2)))
    if fade < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * fade)))
    img.alpha_composite(lay)

# ---------------- compose ----------------
def _plain_bg():
    rng = np.random.default_rng(3)
    arr = np.clip(np.full((H, W, 3), BG, np.int16) + rng.normal(0, 4, (H, W, 1)).astype(np.int16), 0, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")
PLAIN = _plain_bg()
def render_main(t):
    img = PLAIN.copy()
    endp = clamp((t - R.END_T0) / 0.5)
    draw_photo(img, t)
    V.draw_falling(img, t, 0.75)
    V.draw_top(img, t, 1 - endp)
    for s, u, a, yoff in R.active(t): draw_sentence(img, s, u, t, a, yoff)
    for s, a in V.korean_state(t): draw_korean(img, s, a)
    draw_counter(img, t, 1 - endp)
    for c, tf, ta in CW: draw_card(img, c, t, tf, ta)
    if endp > 0: V.draw_end(img, t, endp)
    return img

FRAME0 = None
def frame(t):
    global FRAME0
    if t >= R.LOOP_T0:
        if FRAME0 is None: FRAME0 = render_main(0.0).convert("RGB")
        k = ease_in_out((t - R.LOOP_T0) / (DUR - 1 / FPS - R.LOOP_T0))
        return Image.blend(render_main(R.LOOP_T0).convert("RGB"), FRAME0, k)
    return render_main(t).convert("RGB")

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "sheet":
        ts = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [i for i in range(int(DUR))]
        th = [frame(t).resize((270, 480), Image.LANCZOS) for t in ts]
        cols = 6; rows = math.ceil(len(th) / cols)
        sheet = Image.new("RGB", (cols * 270, rows * 500), (30, 30, 30)); dd = ImageDraw.Draw(sheet)
        for i, im in enumerate(th):
            sheet.paste(im, ((i % cols) * 270, (i // cols) * 500 + 20)); dd.text(((i % cols) * 270 + 6, (i // cols) * 500 + 2), f"{ts[i]:.1f}s", fill=(255, 255, 255))
        sheet.save(ROOT + "sheet5.jpg", quality=85)
    elif mode == "still":
        frame(float(sys.argv[2])).save(ROOT + f"v5_{sys.argv[2]}.jpg", quality=90)
    elif mode == "arrivals":
        print(ARRIVALS)
    elif mode == "video":
        n = int(DUR * FPS)
        p = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                              "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", ROOT + "mix5.wav",
                              "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                              "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                              ROOT + "out5.mp4"], stdin=subprocess.PIPE)
        for i in range(n): p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close(); p.wait(); print("done")
