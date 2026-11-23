"""Cloud bank that grows by one cloud each time an expression card pops."""
import math
import numpy as np
from PIL import Image, ImageDraw
import render as R
from render import clamp, ease_out, kr, tw, MARK, INK, WHITE, LAV, ROSE, CARDWIN

CARD_TS = [c["t"] for c, _ in CARDWIN]
N_CARDS = len(CARD_TS)
SRC = (300, 1250)
BASE_X, BASE_Y = 130, 1462
# heap: 3 on the bottom, 2 in the middle, 1 on top
SLOTS = [(-62, 0, 92), (0, 6, 100), (62, 0, 92), (-32, -48, 88), (34, -46, 88), (2, -92, 84)]
ORDER = [1, 0, 2, 3, 4, 5]
SLOTS = [SLOTS[i] for i in ORDER][:N_CARDS]

EVENTS = [dict(k=k, t0=tc + 0.15, t1=tc + 0.8) for k, tc in enumerate(CARD_TS)]
ARRIVALS = [e["t1"] for e in EVENTS]

FLAB = kr(26)
from PIL import ImageFilter
_cl = {}
def cloud(emoji, size):
    if size in _cl: return _cl[size]
    e = emoji("☁️", size)
    pad = 10
    a = Image.new("L", (e.width + pad * 2, e.height + pad * 2), 0); a.paste(e.getchannel("A"), (pad, pad))
    ring = a.filter(ImageFilter.MaxFilter(7))
    out = Image.new("RGBA", a.size, (0, 0, 0, 0))
    sh = Image.new("RGBA", a.size, (31, 63, 99, 0)); sh.putalpha(a.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.35)))
    out.alpha_composite(sh, (0, 5))
    rim = Image.new("RGBA", a.size, LAV + (0,)); rim.putalpha(ring)
    out.alpha_composite(rim)
    out.alpha_composite(e, (pad, pad))
    _cl[size] = out
    return out
def draw_pile(img, t, emoji, fade=1.0):
    if fade <= 0: return
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    got = 0
    for e in EVENTS:
        if t < e["t0"]: continue
        dx, dy, sz = SLOTS[e["k"]]
        x1, y1 = BASE_X + dx, BASE_Y + dy
        bob = 4 * math.sin(2 * math.pi * (t / 3.0 + e["k"] * 0.27))
        if t < e["t1"]:                       # cloud drifts over in a soft arc
            p = (t - e["t0"]) / (e["t1"] - e["t0"]); q = ease_out(p)
            x = SRC[0] + (x1 - SRC[0]) * q
            y = SRC[1] + (y1 - SRC[1]) * q - 150 * math.sin(math.pi * p)
            size = int(sz * (0.5 + 0.5 * min(1, p * 1.5)))
        else:                                 # "퐁" — soft puff on landing
            got = e["k"] + 1
            d = t - e["t1"]
            x, y = x1, y1 + bob
            size = int(sz * (1 + 0.22 * math.exp(-d * 7) * math.cos(d * 22)))
        im = cloud(emoji, max(8, size))
        lay.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
        d = t - e["t1"]
        if 0 <= d < 0.35:
            r = 20 + 90 * d; a = int(200 * (1 - d / 0.35))
            ImageDraw.Draw(lay).ellipse((x1 - r, y1 - r * 0.7, x1 + r, y1 + r * 0.7), outline=LAV + (a,), width=4)
    # counter floats just above the current top of the bank
    h = 0.0
    tops = [BASE_Y + 30]
    for e in EVENTS:
        if t >= e["t1"]:
            dx, dy, sz = SLOTS[e["k"]]
            tops.append(BASE_Y + dy - sz * 0.45)
    target = min(tops)
    top = target - 40
    label = f"모은 표현 {got}/{N_CARDS}"
    w = tw(FLAB, label) + 36
    bump = 0
    for e in EVENTS:
        dd = t - e["t1"]
        if 0 <= dd < 0.4: bump = 0.18 * math.exp(-dd * 8)
    hw = w / 2 * (1 + bump); hh = 22 * (1 + bump)
    dr = ImageDraw.Draw(lay)
    dr.rounded_rectangle((BASE_X - hw, top - hh, BASE_X + hw, top + hh), radius=int(hh), fill=WHITE + (240,), outline=LAV + (255,), width=3)
    dr.text((BASE_X - tw(FLAB, label) / 2, top - 18), label, font=FLAB, fill=INK)
    if fade < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * fade)))
    img.alpha_composite(lay)
