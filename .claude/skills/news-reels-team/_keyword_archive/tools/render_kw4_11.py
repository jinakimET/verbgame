#!/usr/bin/env python3
"""v4 kw_11 'technically' - refined neo-brutalism, minimal motion (slide/fade only).
Key image: speech bubble with prison bars + tiny room outline + magnifier/tick (no text), kept on screen.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw4_11.py [--frames]"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird as BIRD

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
RID = "11"
OUT = f"{ROOT}/06_keyword_reels/v4"; FR = f"{OUT}/frames"
MP3 = f"{ROOT}/audio/v3/kw_{RID}.mp3"
W, H, FPS, TAIL = 1080, 1920, 30, 0.7
BOLD_F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
BLACK_F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
def hx(s): s = s.lstrip("#"); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
INK, PAPER, BG, OLIVE, OLIVE_L, SAND, RUST, SHADOW = (hx(c) for c in
    ("22221D", "FBF8EE", "E7E2CE", "A9AE82", "CDD0A8", "DDD4B6", "9A4425", "5A5E3A"))
OL = 3; SH = 8
def lum(c):
    f = lambda v: (v/255/12.92) if v/255 <= .03928 else ((v/255+.055)/1.055) ** 2.4
    return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)
_fc = {}
def font(size, path=BOLD_F):
    k = (size, path)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size, index=1)
    return _fc[k]
def mix(a, b, p): return tuple(int(round(x + (y - x) * p)) for x, y in zip(a, b))
def ease(u): u = min(1, max(0, u)); return 1 - (1 - u) ** 3

D = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[RID]
words = D["words"]; BEATS = D["beats"]; BT = [b["start"] for b in BEATS]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3],
                           capture_output=True, text=True).stdout)
TOTAL = round((dur + TAIL) * FPS) / FPS

# ---- beat definitions: card colour, hl token idxs ----
CARD = {"hook": PAPER, "question": SAND, "answer": OLIVE_L, "meaning": OLIVE_L, "ex1_en": PAPER, "ex1_ko": SAND, "ex2_en": PAPER, "ex2_ko": SAND}
HL = {1: [1, 2], 4: [0, 1]}  # beat idx -> token idx highlighted (hook2 '엄밀히 말하면', meaning)
HL.update({5: [0], 6: [0, 1], 7: [0], 8: [0, 1]})
CX0, CY0, CW, CH = 66, 650, 776, 540   # card box (shadow reaches x=850)
PADX = 40
TOK = []
for bi, b in enumerate(BEATS):
    toks = b["show"].split(" "); assert len(toks) == b["n_words"], (bi, toks)
    TOK.append([(t, words[b["first_word_idx"] + i]["s"]) for i, t in enumerate(toks)])

def wrap(toks, size, maxw, fpath=BOLD_F):
    f = font(size, fpath); sp = f.getlength(" "); rows = [[]]; x = 0
    for i, (t, _) in enumerate(toks):
        w = f.getlength(t)
        if rows[-1] and x + sp + w > maxw: rows.append([]); x = 0
        x += (sp if rows[-1] else 0) + w; rows[-1].append(i)
    return rows
def fit(toks, maxw=CW - 2 * PADX, maxh=CH - 90, smax=76, smin=44):
    for s in range(smax, smin - 1, -2):
        rows = wrap(toks, s, maxw)
        if len(rows) * s * 1.55 <= maxh: return s, rows
    return smin, wrap(toks, smin, maxw)

def rect(d, box, fill, k=1, sh=SH, shc=SHADOW):
    x0, y0, x1, y1 = box
    if sh: d.rectangle((x0 + sh, y0 + sh, x1 + sh, y1 + sh), fill=shc)
    d.rectangle(box, fill=fill, outline=INK, width=OL)

LAY = {}
for bi in range(len(BEATS)):
    if BEATS[bi]["role"] == "answer": continue
    s, rows = fit(TOK[bi]); LAY[bi] = (s, rows)

def card_layer(bi, t):
    im = Image.new("RGBA", (CW + SH + 4, CH + SH + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fill = CARD[BEATS[bi]["role"]]
    rect(d, (0, 0, CW, CH), fill)
    toks = TOK[bi]; dim = mix(fill, INK, .25)
    sp_p = lambda s: min(1, max(0, (t - s) / 0.14))
    if BEATS[bi]["role"] == "answer":
        f1 = font(60); p = sp_p(toks[0][1]); d.text((PADX, 105), toks[0][0], font=f1, fill=mix(dim, INK, p))
        size = 118
        while font(size, BLACK_F).getlength("technically") > CW - 2 * PADX - 70: size -= 2
        f = font(size, BLACK_F); w = f.getlength("technically"); bw = w + 56; bh = size * 1.45
        p = sp_p(toks[1][1]); e = ease((t - toks[1][1]) / 0.55)
        bx = PADX + (1 - e) * -50; by = 225
        if p > 0:
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
            rect(ld, (bx, by, bx + bw, by + bh), RUST)
            ld.text((bx + 28, by + bh / 2), "technically", font=f, fill=PAPER, anchor="lm")
            a = lay.getchannel("A").point(lambda v: int(v * p)); lay.putalpha(a); im.alpha_composite(lay)
        else:
            d.text((PADX + 28, by + bh / 2), "technically", font=f, fill=dim, anchor="lm")
        return im
    size, rows = LAY[bi]; f = font(size); sp = f.getlength(" "); lh = size * 1.55
    top = (CH - len(rows) * lh) / 2; hl = set(HL.get(bi, []))
    for r, row in enumerate(rows):
        x = PADX; cy = top + lh * (r + .5); xs = []
        for i in row:
            w = f.getlength(toks[i][0]); xs.append((i, x, w)); x += w + sp
        # highlight boxes first (merge runs)
        for j, (i, x, w) in enumerate(xs):
            if i in hl:
                p = sp_p(toks[i][1]); nxt = xs[j + 1] if j + 1 < len(xs) and xs[j + 1][0] in hl else None
                x1 = nxt[1] if nxt else x + w + 8
                if p > 0:
                    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
                    rect(ld, (x - 12, cy - size * .68, x1 - (0 if nxt else 0), cy + size * .68), RUST, sh=6)
                    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * p))); im.alpha_composite(lay)
        for (i, x, w) in xs:
            p = sp_p(toks[i][1]); full = PAPER if i in hl else INK
            d.text((x, cy), toks[i][0], font=f, fill=mix(dim, full, p), anchor="lm")
    return im

# ---- key image (pre-rendered at 2x) ----
K = 2
def new2(w, h): im = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); return im, ImageDraw.Draw(im)
def fin(im): return im.resize((im.width // K, im.height // K), Image.LANCZOS)
BX, BY, BWd, BHt = 70, 282, 340, 230       # bubble
def bubble_poly(o=0):
    return [(BX - o, BY - o), (BX + BWd + o, BY - o), (BX + BWd + o, BY + BHt + o), (BX + 120 + o, BY + BHt + o),
            (BX + 40, BY + BHt + 66 + o), (BX + 56 - o, BY + BHt + o), (BX - o, BY + BHt + o)]
def draw_poly(d, pts, off=0, **kw): d.polygon([((x + off) * K, (y + off) * K) for x, y in pts], **kw)
def make_bubble():
    im, d = new2(W, 640)
    draw_poly(d, bubble_poly(), off=SH, fill=SHADOW)
    pts = bubble_poly(); d.polygon([(x * K, y * K) for x, y in pts], fill=PAPER)
    d.line([(x * K, y * K) for x, y in pts + [pts[0]]], fill=INK, width=OL * K, joint="curve")
    return fin(im)
def make_bars():
    im, d = new2(W, 640)
    for i in range(5):
        x = BX + 34 + i * 68
        d.rectangle(((x - 6) * K, (BY + 3) * K, (x + 6) * K, (BY + BHt - 3) * K), fill=INK)
    return fin(im)
RX, RY, RW, RH = 462, 326, 236, 196
def make_room():
    im, d = new2(W, 640)
    d.rectangle(((RX + SH) * K, (RY + SH) * K, (RX + RW + SH) * K, (RY + RH + SH) * K), fill=SHADOW)
    d.rectangle((RX * K, RY * K, (RX + RW) * K, (RY + RH) * K), fill=PAPER, outline=INK, width=OL * K)
    fy = RY + RH - 40   # floor line
    d.line((RX * K, fy * K, (RX + RW) * K, fy * K), fill=INK, width=OL * K)
    d.rectangle(((RX + 120) * K, (RY + 30) * K, (RX + 196) * K, (RY + 92) * K), fill=OLIVE_L, outline=INK, width=OL * K)  # window
    d.line(((RX + 158) * K, (RY + 30) * K, (RX + 158) * K, (RY + 92) * K), fill=INK, width=OL * K)
    d.rectangle(((RX + 18) * K, (fy - 40) * K, (RX + 104) * K, fy * K), fill=OLIVE, outline=INK, width=OL * K)  # bed
    d.rectangle(((RX + 18) * K, (fy - 58) * K, (RX + 36) * K, fy * K), fill=OLIVE, outline=INK, width=OL * K)
    return fin(im)
MCX, MCY, MR = 748, 372, 54
def make_mag():
    im, d = new2(W, 640)
    ex = lambda a: [a]
    d.line(((MCX + 38) * K, (MCY + 38) * K, (MCX + 92) * K, (MCY + 92) * K), fill=INK, width=22 * K)
    d.line(((MCX + 38) * K, (MCY + 38) * K, (MCX + 92) * K, (MCY + 92) * K), fill=RUST, width=14 * K)
    d.ellipse(((MCX - MR + SH) * K, (MCY - MR + SH) * K, (MCX + MR + SH) * K, (MCY + MR + SH) * K), fill=SHADOW)
    d.ellipse(((MCX - MR) * K, (MCY - MR) * K, (MCX + MR) * K, (MCY + MR) * K), fill=PAPER, outline=INK, width=6 * K)
    tick = [(MCX - 26, MCY + 2), (MCX - 8, MCY + 22), (MCX + 28, MCY - 22)]
    d.line([(x * K, y * K) for x, y in tick], fill=RUST, width=11 * K, joint="curve")
    return fin(im)
BUBBLE, BARS, ROOM, MAG = make_bubble(), make_bars(), make_room(), make_mag()
IMG_Y = 238
def paste_a(img, layer, x, y, a=1.0):
    if a <= 0: return
    if a < 1: layer = layer.copy(); layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    img.paste(layer, (int(x), int(y)), layer)

# ---- bird ----
ENV = BIRD.envelope(MP3, FPS, int(TOTAL * FPS) + 3)
_bc = {}
def bird_img(a):
    q = round(a * 16) / 16
    if q in _bc: return _bc[q]
    sp = BIRD.sprite(q); al = sp.getchannel("A"); ol = al.filter(ImageFilter.MaxFilter(7)); pad = 16
    im = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
    ink = Image.new("RGBA", ol.size, INK + (255,)); ink.putalpha(ol)
    im.alpha_composite(ink, (pad, pad)); im.alpha_composite(sp, (pad, pad)); _bc[q] = im; return im
BCX, PLAT_TOP = 640, 1440
def draw_bird(img, fi):
    d = ImageDraw.Draw(img); pw = 300
    rect(d, (BCX - pw // 2, PLAT_TOP, BCX + pw // 2, PLAT_TOP + 26), OLIVE)
    b = bird_img(float(ENV[fi])); img.paste(b, (int(BCX - b.width / 2), int(PLAT_TOP - b.height + 24)), b)

HANDLE = "지나쌤영어  @jina.ssam_english"
def beat_idx(t): return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
TR = 0.45
def frame(t, fi):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    # flat olive band behind the key image
    d.rectangle((0, IMG_Y, W, IMG_Y + 372), fill=OLIVE); d.line((0, IMG_Y, W, IMG_Y), fill=INK, width=OL); d.line((0, IMG_Y + 372, W, IMG_Y + 372), fill=INK, width=OL)
    paste_a(img, BUBBLE, 0, 0); paste_a(img, ROOM, 0, 0)
    bars_a = 1.0 - 0.6 * ease((t - words[15]["s"]) / 0.7)         # bars lift away at "감옥은 아니고"
    paste_a(img, BARS, 0, 0, bars_a)
    me = ease((t - words[13]["s"]) / 0.6)                          # magnifier slides in at "엄밀히"
    paste_a(img, MAG, (1 - me) * 40, 0, me)
    bi = beat_idx(t); dt = t - BT[bi]
    def put_card(i, a, dy):
        c = card_layer(i, t)
        if a < 1: c.putalpha(c.getchannel("A").point(lambda v: int(v * a)))
        img.paste(c, (CX0, int(CY0 + dy)), c)
    if bi > 0 and dt < TR:
        e = ease(dt / TR); put_card(bi - 1, 1 - e, -18 * e); put_card(bi, e, 28 * (1 - e))
    else:
        put_card(bi, 1, 0)
    draw_bird(img, fi)
    d = ImageDraw.Draw(img); d.text((W // 2, 1588), HANDLE, font=font(38), fill=INK, anchor="mm")
    return img

MARKS = {"hook1_0.0": 0.0, "hook1_0.2": 0.2, "hook1_mid": 3.9, "hook2_start": 7.2, "hook2_end": 9.2, "question": 12.8,
         "answer_pre": 15.5, "answer_in": 16.9, "meaning": 19.0, "ex1_en_a": 21.9, "ex1_en": 25.0, "ex1_ko": 28.5,
         "ex2_en": 32.5, "ex2_ko": 35.0, "end": TOTAL - 0.05}
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
    pairs = {"ink/paper": (INK, PAPER), "ink/sand": (INK, SAND), "ink/olive_l": (INK, OLIVE_L), "ink/olive (band)": (INK, OLIVE),
             "paper/rust (hl, answer)": (PAPER, RUST), "ink/bg (handle)": (INK, BG)}
    for k, (a, b) in pairs.items(): print(f"{contrast(a, b):5.2f}  {k}")
if __name__ == "__main__":
    report_contrast()
    if "--frames" in sys.argv:
        os.makedirs(FR, exist_ok=True)
        for k, v in MARKS.items(): frame(v, int(v * FPS)).save(f"{FR}/kw_{RID}_{k}.png")
    else: render()
