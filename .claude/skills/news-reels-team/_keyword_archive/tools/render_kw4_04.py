#!/usr/bin/env python3
"""kw4 / 04 'as of' (2026-11-25 episode, script v3): restrained INFINITE ZOOM through Paris facade layers.
Palette: deep blue / cream / gold, near-black text. No scramble, no particles.
Key image (always visible): text-free calendar with ONE highlighted day + Paris rooftop row of tiny lit windows; bird stands on the ridge.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw4_04.py [--frames t1,t2,...]
Output: 06_keyword_reels/v4/kw_04.mp4, frames in 06_keyword_reels/v4/frames/"""
import os, sys, json, math, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
RID = "04"; W, H = 1080, 1920; FPS = 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels/v4"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
MP3 = f"{ROOT}/audio/v3/kw_{RID}.mp3"
FD = "/usr/share/fonts/opentype/noto/"
_fc = {}
def font(sz, fam="Sans", w="Bold"):
    k = (sz, fam, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}Noto{fam}CJK-{w}.ttc", sz, index=1)
    return _fc[k]

# palette (muted deep blue / cream / gold, near-black text)
BLUE_D = (24, 38, 68); BLUE_M = (41, 62, 100); CREAM = (244, 236, 218); GOLD = (201, 162, 75); INK = (22, 24, 32)
def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)
def blend(a, b, t): return tuple(int(round(x * (1 - t) + y * t)) for x, y in zip(a, b))
PANEL_A = 0.88

# ------------------------------------------------------------------ script / words
D = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[RID]
words = D["words"]; BEATS = D["beats"]
CORRECTED = []
for w in words:   # Scribe zero-length words -> minimum 0.08 s
    if w["e"] - w["s"] < 0.08:
        CORRECTED.append((w["t"], w["s"])); w["e"] = round(w["s"] + 0.08, 3)
AUDIO_DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
TOTAL = AUDIO_DUR + TAIL; NF = int(round(TOTAL * FPS))
def tok(text, idxs, hl=False):
    """screen token tied to spoken word indices (start of first word; solid by corrected end of last)."""
    s = words[idxs[0]]["s"]; e = words[idxs[-1]]["e"]
    return dict(text=text, s=s, e=min(e, s + .45) if e - s > .45 else max(e, s + .18), hl=hl)
def static(text, hl=False): return dict(text=text, s=-9, e=-9, hl=hl)
# beat show texts must equal screen tokens joined
SHOW = [b["show"] for b in BEATS]
H1 = [tok("파리의", [0]), tok("화려한", [1]), tok("건물", [2]), tok("꼭대기에는", [3]), tok("아주", [4]), tok("작은", [5]), tok("방이", [6]),
      tok("9만", [7, 8], True), tok("개가", [9]), tok("넘게", [10]), tok("있대요.", [11])]
H2 = [tok("이", [12]), tok("통계는", [13]), tok("2022년", [14, 15, 16], True), tok("기준이에요.", [17])]
QU = [tok("이", [18]), tok("기준이라는", [19]), tok("말은", [20]), tok("영어로?", [21])]
EX1E = [tok("As", [29], True), tok("of", [30], True), tok("2022,", [31, 32]), tok("Paris", [33]), tok("had", [34]), tok("over", [35]),
        tok("90,000", [36, 37]), tok("of", [38]), tok("these", [39]), tok("tiny", [40]), tok("rooms.", [41])]
EX1K = [tok("2022년", [42, 43, 44]), tok("기준으로", [45], True), tok("파리에는", [46]), tok("이런", [47]), tok("작은", [48]), tok("방이", [49]),
        tok("9만", [50, 51]), tok("개가", [52]), tok("넘었다.", [53])]
EX2E = [tok("As", [54], True), tok("of", [55], True), tok("today,", [56]), tok("the", [57]), tok("sale", [58]), tok("has", [59]), tok("ended.", [60])]
EX2K = [tok("오늘", [61]), tok("기준으로", [62], True), tok("세일은", [63]), tok("끝났다.", [64])]
for texts, toks in ((SHOW[0], H1), (SHOW[1], H2), (SHOW[2], QU), (SHOW[5], EX1E), (SHOW[6], EX1K), (SHOW[7], EX2E), (SHOW[8], EX2K)):
    assert " ".join(t["text"] for t in toks) == texts, (texts, [t["text"] for t in toks])
assert SHOW[3] == "정답은… as of" and SHOW[4] == "기준으로, 현재로, 라는 뜻이에요"

# ------------------------------------------------------------------ text blocks
CX = 456; TEXT_MAXW = 700; PX0, PX1 = 62, 850
def wrap(toks, f, maxw):
    sp = f.getlength(" "); lines = [[]]; cur = 0
    for t in toks:
        w = f.getlength(t["text"])
        if lines[-1] and cur + sp + w > maxw: lines.append([]); cur = 0
        cur += (sp if lines[-1] else 0) + w; lines[-1].append(t)
    return lines
class Block:
    """lines: list of (tokens, size, fam, weight); gap_after: extra px after line index"""
    def __init__(self, line_specs, cy, lh=1.36, gaps=None):
        gaps = gaps or {}; self.lines = []; y = 0; rows = []
        for li, (toks, size, fam, wt) in enumerate(line_specs):
            f = font(size, fam, wt); h = size * lh
            rows.append((toks, f, size, y + h / 2)); y += h + gaps.get(li, 0)
        self.h = y; top = max(cy - y / 2, 262); bot = top + y
        if bot > 1120: top -= bot - 1120
        self.top = top; self.items = []
        for toks, f, size, yc in rows:
            sp = f.getlength(" "); ws_ = [f.getlength(t["text"]) for t in toks]; tot = sum(ws_) + sp * (len(toks) - 1)
            x = CX - tot / 2
            for t, w in zip(toks, ws_):
                self.items.append(dict(t=t, f=f, size=size, x=x, w=w, y=top + yc)); x += w + sp
        self.pad = 54
        self.px0, self.px1 = PX0, PX1; self.py0 = top - self.pad; self.py1 = top + y + self.pad
        self.panel = self._panel()
        # highlight groups (consecutive hl tokens on one line)
        self.hl = []; cur = None
        for it in self.items:
            if it["t"]["hl"]:
                if cur and abs(cur[-1]["y"] - it["y"]) < 1 and cur[-1] is self.items[self.items.index(it) - 1]: cur.append(it)
                else: cur = [it]; self.hl.append(cur)
            else: cur = None
    def _panel(self):
        S = 2; w = self.px1 - self.px0; h = int(self.py1 - self.py0)
        im = Image.new("RGBA", ((w + 8) * S, (h + 8) * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((4 * S, 4 * S, (w + 4) * S, (h + 4) * S), radius=44 * S, fill=CREAM + (int(255 * PANEL_A),), outline=GOLD + (255,), width=3 * S)
        return im.resize((w + 8, h + 8), Image.LANCZOS)
    def draw(self, layer, t, dy=0):
        layer.alpha_composite(self.panel, (self.px0 - 4, int(round(self.py0 - 4 + dy))))
        hlay = Image.new("RGBA", layer.size, (0, 0, 0, 0)); d = ImageDraw.Draw(hlay)
        for grp in self.hl:
            a, b = grp[0], grp[-1]; sz = a["size"]
            p = fillp(a["t"], t); al = int(255 * (.35 + .65 * p))
            x0, x1 = a["x"] - 14, b["x"] + b["w"] + 14; yc = a["y"] + dy
            d.rounded_rectangle((x0, yc - sz * .62, x1, yc + sz * .62), radius=int(sz * .3), fill=GOLD + (al,))
        layer.alpha_composite(hlay); d = ImageDraw.Draw(layer)
        for it in self.items:
            p = fillp(it["t"], t); rise = 8 * (1 - ease(p))
            col = blend(CREAM, INK, .24 + .76 * ease(p))   # ghost -> full near-black
            d.text((it["x"], it["y"] + dy + rise), it["t"]["text"], font=it["f"], fill=col + (255,), anchor="lm")
def ease(p): p = min(1, max(0, p)); return p * p * (3 - 2 * p)
def fillp(tk, t):
    if tk["s"] < 0: return 1.0
    return min(1, max(0, (t - tk["s"]) / max(.12, tk["e"] - tk["s"] if tk["e"] > tk["s"] else .18)))

def lines_of(toks, size, fam="Sans", wt="Bold"):
    f = font(size, fam, wt)
    return [(ln, size, fam, wt) for ln in wrap(toks, f, TEXT_MAXW)]
# hook = both hook beats together, visible from frame 0
HOOK = Block(lines_of(H1, 62) + lines_of(H2, 62), 690, gaps={len(wrap(H1, font(62), TEXT_MAXW)) - 1: 26})
QUES = Block(lines_of(QU, 92), 640)
ANS_SZ = 300
while font(ANS_SZ, "Serif", "Black").getlength("as of") > 650: ANS_SZ -= 4
ANSW = Block([([tok("정답은…", [22])], 72, "Sans", "Bold"), ([tok("as", [23], True), tok("of", [24], True)], ANS_SZ, "Serif", "Black")], 640, lh=1.30, gaps={0: 34})
MEAN = Block([([static("as of", True)], 66, "Serif", "Black"), ([tok("기준으로,", [25])], 108, "Sans", "Black"), ([tok("현재로,", [26])], 108, "Sans", "Black"),
              ([tok("라는", [27]), tok("뜻이에요", [28])], 70, "Sans", "Bold")], 640, lh=1.34, gaps={0: 26, 2: 24})
EX1E_B = Block(lines_of(EX1E, 76, "Serif", "Bold"), 640)
EX1K_B = Block(lines_of(EX1K, 78), 640)
EX2E_B = Block(lines_of(EX2E, 84, "Serif", "Bold"), 640)
EX2K_B = Block(lines_of(EX2K, 86), 640)
# scenes: (block, start time, end time)  (hook spans beats 0-1; others one beat each)
BT = [b["start"] for b in BEATS]
SCENES = [("hook", HOOK, 0.0, BT[2]), ("question", QUES, BT[2], BT[3]), ("answer", ANSW, BT[3], BT[4]), ("meaning", MEAN, BT[4], BT[5]),
          ("ex1_en", EX1E_B, BT[5], BT[6]), ("ex1_ko", EX1K_B, BT[6], BT[7]), ("ex2_en", EX2E_B, BT[7], BT[8]), ("ex2_ko", EX2K_B, BT[8], 1e9)]
LEAD, XF = 0.22, 0.34   # scene fades in from start-LEAD over XF seconds; previous fades out over the same span

# ------------------------------------------------------------------ infinite zoom (facade layers nested via arch openings)
S2 = 2; VX, VY = 540, 960
OPEN = (270, 480, 810, 1440)   # opening = exactly half the canvas around the vanishing point
VARS = [dict(wall=(36, 56, 94), wall2=(30, 47, 82), roof=(54, 70, 100)),
        dict(wall=(44, 66, 106), wall2=(35, 53, 90), roof=(60, 77, 108)),
        dict(wall=(30, 48, 84), wall2=(26, 41, 73), roof=(48, 63, 92))]
def make_layer(v):
    g = VARS[v]; im = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    X = lambda *a: [int(x * S2) for x in a]
    # sky strip behind roofline
    for y in range(0, 190):
        c = blend((58, 78, 118), (112, 118, 140), y / 190); d.rectangle(X(0, y, W, y + 1), fill=c + (255,))
    # wall
    d.rectangle(X(0, 300, W, H), fill=g["wall"] + (255,))
    for y in range(300, H, 160): d.rectangle(X(0, y + 150, W, y + 156), fill=g["wall2"] + (255,))
    # mansard roof + chimneys + dormers
    d.polygon(X(0, 330, 70, 196, 1010, 196, 1080, 330), fill=g["roof"] + (255,))
    for cx_ in (150, 430, 760, 950): d.rectangle(X(cx_, 120, cx_ + 40, 200), fill=blend(g["roof"], BLUE_D, .35) + (255,))
    for k in range(13):
        cx_ = 60 + k * 80
        d.polygon(X(cx_ - 20, 262, cx_, 238, cx_ + 20, 262), fill=blend(g["roof"], CREAM, .12) + (255,))
        d.rounded_rectangle(X(cx_ - 12, 262, cx_ + 12, 300), radius=int(12 * S2), fill=blend(GOLD, CREAM, .25 + .1 * ((k + v) % 3)) + (255,))
    d.rectangle(X(0, 326, W, 338), fill=GOLD + (255,))
    # wall windows (tall, arched) with balcony rails, skipping the opening
    ox0, oy0, ox1, oy1 = OPEN
    for row, y in enumerate(range(380, H - 60, 190)):
        for k in range(7):
            cx_ = 40 + k * 165 + (80 if row % 2 else 0) * 0
            wx0, wx1, wy0, wy1 = cx_ - 36, cx_ + 36, y, y + 130
            if wx1 > ox0 - 30 and wx0 < ox1 + 30 and wy1 > oy0 - 30 and wy0 < oy1 + 30: continue
            lit = (row * 3 + k + v) % 4 != 0
            d.rounded_rectangle(X(wx0 - 5, wy0 - 5, wx1 + 5, wy1 + 5), radius=int(40 * S2), fill=blend(g["wall"], GOLD, .55) + (255,))
            d.rounded_rectangle(X(wx0, wy0, wx1, wy1), radius=int(36 * S2), fill=(blend(GOLD, CREAM, .45) if lit else blend(g["wall2"], BLUE_D, .5)) + (255,))
            d.rectangle(X(wx0 - 12, wy1 + 8, wx1 + 12, wy1 + 14), fill=blend(g["wall"], GOLD, .7) + (255,))
    # opening (arched, transparent) with gold rim + soft inner shadow
    hole = Image.new("L", im.size, 0); hd = ImageDraw.Draw(hole)
    hd.rounded_rectangle(X(ox0, oy0, ox1, oy1), radius=int(190 * S2), fill=255)
    hd.rectangle(X(ox0, (oy0 + oy1) / 2, ox1, oy1), fill=255)
    rim = Image.new("RGBA", im.size, (0, 0, 0, 0)); rd = ImageDraw.Draw(rim)
    rd.rounded_rectangle(X(ox0 - 10, oy0 - 10, ox1 + 10, oy1 + 10), radius=int(200 * S2), fill=GOLD + (255,))
    rd.rectangle(X(ox0 - 10, (oy0 + oy1) / 2, ox1 + 10, oy1 + 10), fill=GOLD + (255,))
    rim2 = Image.new("RGBA", im.size, (0, 0, 0, 0)); rd2 = ImageDraw.Draw(rim2)
    rd2.rounded_rectangle(X(ox0 - 28, oy0 - 28, ox1 + 28, oy1 + 28), radius=int(218 * S2), fill=BLUE_D + (255,))
    rd2.rectangle(X(ox0 - 28, (oy0 + oy1) / 2, ox1 + 28, oy1 + 28), fill=BLUE_D + (255,))
    im.alpha_composite(rim2); im.alpha_composite(rim)
    a = np.array(im.getchannel("A")); a[np.array(hole) > 0] = 0
    arr = np.array(im); arr[..., 3] = a
    arr[..., :3] = (arr[..., :3].astype(np.float32) * (a[..., None] / 255.0)).astype(np.uint8)   # premultiplied
    return arr
LAYERS = [make_layer(v) for v in range(3)]
BASE = np.zeros((H, W, 3), np.float32); BASE[:] = BLUE_D
NLAY = 6
def zoom_u(t):   # octaves travelled: slow constant drift + one soft push at the answer
    ta = BT[3]; push = 0.30 * ease((t - ta) / 1.4)
    return 0.095 * t + push
def background(t):
    u = zoom_u(t); n0 = int(math.floor(u)); g = u - n0
    acc = BASE.copy()
    for j in range(-(NLAY - 1), 1):          # smallest first
        s = 2.0 ** (j + g); n = n0 + j
        src = LAYERS[n % 3]
        if s < 1:
            w_, h_ = max(2, int(round(W * s))), max(2, int(round(H * s)))
            small = cv2.resize(src, (w_, h_), interpolation=cv2.INTER_AREA)
            lay = np.zeros((H, W, 4), np.uint8)
            x0, y0 = int(round(VX - VX * s)), int(round(VY - VY * s)); lay[y0:y0 + h_, x0:x0 + w_] = small[:min(h_, H - y0), :min(w_, W - x0)]
        else:
            M = np.float32([[s / 2, 0, (1 - s) * VX], [0, s / 2, (1 - s) * VY]])
            lay = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        al = 1.0
        if j == -(NLAY - 1): al = ease(g)          # innermost fades in
        if j == 0: al = 1 - ease(g)                # outermost fades out as its opening fills the frame
        f = lay.astype(np.float32); a = f[..., 3:4] / 255.0 * al
        hz = min(.62, max(0.0, (1 - s) * .55 + .08 if s < 1 else 0.0))   # distance haze toward deep blue
        rgb = f[..., :3] * al
        rgb = rgb * (1 - hz) + np.array(BLUE_D, np.float32) * a * hz
        acc = rgb + acc * (1 - a)
    return acc
# vignette to keep the edges calm
yy = np.linspace(-1, 1, H, dtype=np.float32)[:, None]; xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
VIG = (1 - 0.22 * np.clip((xx ** 2 * .6 + yy ** 2 * .9), 0, 1.4))[..., None]

# ------------------------------------------------------------------ key image: calendar + rooftop windows (always visible)
def make_calendar():
    S = 3; w, h = 250, 238; pad = 20
    im = Image.new("RGBA", ((w + 2 * pad) * S, (h + 2 * pad) * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    X = lambda v: (pad + v) * S
    d.rounded_rectangle((X(5), X(8), X(w + 5), X(h + 8)), radius=26 * S, fill=(8, 12, 24, 90))     # soft shadow
    d.rounded_rectangle((X(0), X(0), X(w), X(h)), radius=26 * S, fill=CREAM + (255,), outline=GOLD + (255,), width=3 * S)
    d.rounded_rectangle((X(0), X(0), X(w), X(58)), radius=26 * S, fill=BLUE_M + (255,)); d.rectangle((X(0), X(34), X(w), X(58)), fill=BLUE_M + (255,))
    for rx in (70, 180): d.rounded_rectangle((X(rx - 7), X(-12), X(rx + 7), X(24)), radius=7 * S, fill=INK + (255,))
    for r in range(5):
        for c in range(7):
            x0 = 14 + c * 32; y0 = 74 + r * 31
            if (r, c) == (2, 3): continue
            d.rounded_rectangle((X(x0), X(y0), X(x0 + 24), X(y0 + 22)), radius=5 * S, fill=blend(CREAM, BLUE_M, .22) + (255,))
    K = 1.2
    return im.resize((int(im.width * K / S), int(im.height * K / S)), Image.LANCZOS)
CAL = make_calendar(); CAL_XY = (50, 1118)
CAL_DAY = (CAL_XY[0] + 1.2 * (20 + 14 + 3 * 32 + 12), CAL_XY[1] + 1.2 * (20 + 74 + 2 * 31 + 11))   # centre of the highlighted day
def make_roof():
    S = 2; im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    X = lambda *a: [int(x * S) for x in a]
    d.rectangle(X(0, 1536, W, H), fill=BLUE_D + (255,))
    d.rectangle(X(0, 1534, W, 1542), fill=GOLD + (255,))
    for y in range(1560, 1920, 60): d.rectangle(X(0, y, W, y + 2), fill=blend(BLUE_D, BLUE_M, .6) + (255,))
    for cx_ in (430, 930): d.rectangle(X(cx_, 1396, cx_ + 38, 1460), fill=blend(BLUE_M, BLUE_D, .3) + (255,)); d.rectangle(X(cx_ - 4, 1390, cx_ + 42, 1398), fill=blend(BLUE_M, GOLD, .25) + (255,))
    d.polygon(X(0, 1534, 70, 1456, 1010, 1456, 1080, 1534), fill=BLUE_M + (255,))
    d.line(X(70, 1456, 1010, 1456), fill=GOLD + (255,), width=4 * S)
    for k in range(15):
        cx_ = 62 + k * 68.5
        d.polygon(X(cx_ - 19, 1486, cx_, 1470, cx_ + 19, 1486), fill=blend(BLUE_M, CREAM, .18) + (255,))
        d.rounded_rectangle(X(cx_ - 14, 1484, cx_ + 14, 1526), radius=int(7 * S), fill=blend(BLUE_M, BLUE_D, .6) + (255,))
    return im.resize((W, H), Image.LANCZOS)
ROOF = make_roof()
WIN = [(62 + k * 68.5, 1484, 1526) for k in range(15)]
def draw_windows(img, t):
    ov = Image.new("RGBA", (W, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for k, (cx_, y0, y1) in enumerate(WIN):
        p = .62 + .38 * math.sin(t * .9 + k * .55); col = blend(blend(GOLD, CREAM, .35), BLUE_M, 1 - p)
        d.rounded_rectangle((cx_ - 10, y0 - 1470 + 4, cx_ + 10, y1 - 1470 - 4), radius=5, fill=col + (255,))
    img.alpha_composite(ov, (0, 1470))
def draw_key(img, t):
    img.alpha_composite(ROOF)
    draw_windows(img, t)
    # single highlighted day: gold cell + soft breathing ring
    br = .5 + .5 * math.sin(t * 1.4)
    ov = Image.new("RGBA", (120, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.ellipse((60 - 28 - 5 * br, 60 - 25 - 5 * br, 60 + 28 + 5 * br, 60 + 25 + 5 * br), outline=GOLD + (int(150 * (1 - br * .5)),), width=3)
    img.alpha_composite(CAL, CAL_XY)
    d = ImageDraw.Draw(img); cx_, cy_ = CAL_DAY
    d.rounded_rectangle((cx_ - 17, cy_ - 16, cx_ + 17, cy_ + 16), radius=7, fill=GOLD + (255,))
    img.alpha_composite(ov, (int(cx_ - 60), int(cy_ - 60)))
HANDLE = Image.new("RGBA", (800, 70), (0, 0, 0, 0))
ImageDraw.Draw(HANDLE).text((400, 35), "지나쌤영어  @jina.ssam_english", font=font(40, "Sans", "Medium"), fill=CREAM + (255,), anchor="mm")
ENV = bird.envelope(MP3, FPS, NF)

# ------------------------------------------------------------------ frame
def scene_alpha(i, st, en):
    t = None
    return None
def render(i):
    t = i / FPS
    bg = background(t) * VIG
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    layer_alpha = []
    for k, (name, blk, st, en) in enumerate(SCENES):
        a_in = 1.0 if k == 0 else ease((t - (st - LEAD)) / XF)
        a_out = 1.0 if k == len(SCENES) - 1 else 1 - ease((t - (en - LEAD)) / XF)
        a = min(a_in, a_out)
        if a <= 0.003: continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dy = (1 - ease((t - (st - LEAD)) / (XF * 1.6))) * 22 if k else 0
        if name == "answer": dy += (1 - ease((t - st) / 1.0)) * 14
        blk.draw(layer, t, dy)
        if name == "answer":     # gold rule drawn under 'as of' after 'of' is spoken
            u = ease((t - words[24]["s"]) / .9)
            if u > 0:
                y = blk.items[-1]["y"] + blk.items[-1]["size"] * .62 + 10 + dy; x0 = CX - 300; ImageDraw.Draw(layer).rounded_rectangle((x0, y, x0 + 600 * u, y + 8), radius=4, fill=GOLD + (255,))
        if a < .999: layer.putalpha(layer.getchannel("A").point(lambda v, a=a: int(v * a)))
        img.alpha_composite(layer)
    draw_key(img, t)
    bird.place(img, float(ENV[min(i, len(ENV) - 1)]), 640, 1460 + int(round(1.5 * math.sin(t * 2.0))))
    img.alpha_composite(HANDLE, ((W - 800) // 2, 1588 - 35))
    return img.convert("RGB")

def checks():
    pairs = [("text INK / panel (worst: cream*.88+dark bg)", INK, blend(CREAM, BLUE_D, 1 - PANEL_A)), ("text INK / cream", INK, CREAM), ("highlight INK / GOLD", INK, GOLD),
             ("handle CREAM / BLUE_D", CREAM, BLUE_D), ("ghost text (not read as final) INK .24 / cream", blend(CREAM, INK, .24), CREAM)]
    for n, a, b in pairs: print(f"contrast {n}: {contrast(a, b):.2f}")
    print("zero-length words corrected to 0.08s:", CORRECTED)
    for name, blk, st, en in SCENES:
        xs = [(it["x"], it["x"] + it["w"]) for it in blk.items]
        print(f"{name:9s} text x {min(a for a, _ in xs):.0f}-{max(b for _, b in xs):.0f}  y {blk.top:.0f}-{blk.top + blk.h:.0f}  panel y {blk.py0:.0f}-{blk.py1:.0f}  sizes {sorted(set(it['size'] for it in blk.items))}")
    print("total", TOTAL, "frames", NF)

if __name__ == "__main__":
    checks()
    if "--frames" in sys.argv:
        for ts in sys.argv[sys.argv.index("--frames") + 1].split(","):
            render(int(round(float(ts) * FPS))).save(f"{FR}/kw_{RID}_t{ts}.png")
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
