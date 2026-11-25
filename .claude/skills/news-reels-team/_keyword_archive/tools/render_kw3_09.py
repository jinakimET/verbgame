#!/usr/bin/env python3
"""kw3_09 'put ~ in jeopardy' : claymorphism + paper cutout + particles.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-23-cnn python3 render_kw3_09.py [--frames t1,t2,...]  (frames only -> v3/frames, no video)"""
import os, sys, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-23-cnn")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
RID = "09"; W, H = 1080, 1920; FPS = 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels/v3"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
MP3 = f"{ROOT}/audio/v3/kw3_{RID}.mp3"
FD = "/usr/share/fonts/opentype/noto/NotoSansCJK-"
def font(sz, w="Black"): return ImageFont.truetype(f"{FD}{w}.ttc", sz, index=1)
SKY = (44, 153, 214); CLOUD = (248, 250, 252); RED = (214, 37, 41); RED2 = (235, 47, 51)
NAVY = (18, 38, 58); LBLUE = (77, 176, 232); DRED = (168, 20, 26)

def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

spec = [r for r in json.load(open(f"{ROOT}/03_script/keyword_scripts_v3.json"))["reels"]]
spec = spec[0] if isinstance(spec, list) and False else None
_s = json.load(open(f"{ROOT}/03_script/keyword_scripts_v3.json"))["reels"]
spec = _s[RID] if isinstance(_s, dict) else [x for x in _s if str(x["id"]) == RID][0]
WK = json.load(open(f"{ROOT}/audio/words_kw_v3.json"))[RID]
words = WK["words"]; BT = [b["start"] for b in WK["beats"]]
assert [b["role"] for b in WK["beats"]] == [b["role"] for b in spec["beats"]]
SPOKEN_END = max(w["e"] for w in words)
AUDIO_DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
TOTAL = AUDIO_DUR + TAIL; NF = int(round(TOTAL * FPS))
def wstart(i): return words[i]["s"]

# ---------------------------------------------------------------- helpers
def blur(L, r): return L.filter(ImageFilter.GaussianBlur(r))
def put(img, spr, x, y):
    x, y = int(round(x)), int(round(y)); sw, sh = spr.size
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(img.width, x + sw), min(img.height, y + sh)
    if x1 <= x0 or y1 <= y0: return
    img.alpha_composite(spr.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))
def fade(spr, a):
    if a >= .999: return spr
    s = spr.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * max(0, a)))); return s
def back(p):
    p = min(1, max(0, p)); c = 1.70158; q = p - 1; return 1 + (c + 1) * q ** 3 + c * q ** 2
def scaled(spr, s, sy=None):
    sy = s if sy is None else sy
    return spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * sy))), Image.BILINEAR)
def mask_draw(w, h, fn, pad=70):
    ss = 2; im = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0); d = ImageDraw.Draw(im)
    fn(d, pad * ss, ss); return im.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
def rrect(w, h, r, pad=70):
    return mask_draw(w, h, lambda d, p, s: d.rounded_rectangle((p, p, p + w * s, p + h * s), radius=r * s, fill=255), pad)
def clay(mask, col, d=None, shadow=True, sh_alpha=.38, sh_off=(0, 20), sh_blur=18, hi=.62, lo=.36):
    bb = mask.getbbox(); bw, bh = bb[2] - bb[0], bb[3] - bb[1]; ms = min(bw, bh)
    d = d or max(4, int(ms * .06)); r = d * 1.2
    m = np.asarray(mask, np.float32) / 255
    a1 = np.asarray(blur(ImageChops.offset(mask, d, d), r), np.float32) / 255
    a2 = np.asarray(blur(ImageChops.offset(mask, -d, -d), r), np.float32) / 255
    pf = np.asarray(blur(mask, max(2, ms * .22)), np.float32) / 255
    hl = m * (1 - a1); sh = m * (1 - a2)
    c = np.array(col, np.float32)[None, None, :]
    rgb = c * (1 + .14 * (pf[..., None] - .55)) + (255 - c) * (hl[..., None] * hi) - c * (sh[..., None] * lo)
    out = np.dstack([np.clip(rgb, 0, 255), np.asarray(mask, np.float32)]).astype(np.uint8)
    spr = Image.fromarray(out, "RGBA")
    if not shadow: return spr
    sm = blur(ImageChops.offset(mask, sh_off[0], sh_off[1]), sh_blur).point(lambda v: int(v * sh_alpha))
    base = Image.new("RGBA", mask.size, NAVY + (0,)); base.putalpha(sm); base.alpha_composite(spr); return base
def txt_flat(t, sz, col, w="Black", pad=6):
    f = font(sz, w); l, tp, r, b = f.getbbox(t)
    im = Image.new("RGBA", (r - l + 2 * pad, int(sz * 1.6)), (0, 0, 0, 0)); ImageDraw.Draw(im).text((pad - l, int(sz * .12)), t, font=f, fill=col + (255,)); return im
def tw(t, sz, w="Black"): f = font(sz, w); return f.getlength(t)
def txt_clay(t, sz, col=CLOUD, pad=40, outline=True):
    f = font(sz); l, tp, r, b = f.getbbox(t); wd, ht = r - l + 44, int(sz * 1.6)
    m = mask_draw(wd, ht, lambda d, p, s: d.text((p - l * s, p + sz * .12 * s), t, font=font(sz * s), fill=255) if False else None, pad)
    ss = 2; big = Image.new("L", ((wd + 2 * pad) * ss, (ht + 2 * pad) * ss), 0)
    ImageDraw.Draw(big).text((pad * ss - l * ss, pad * ss + int(sz * .12 * ss)), t, font=font(sz * ss), fill=255)
    m = big.resize((wd + 2 * pad, ht + 2 * pad), Image.LANCZOS)
    spr = clay(m, col, d=max(3, sz // 22), sh_off=(0, 8), sh_blur=8, sh_alpha=.35, hi=.5, lo=.3)
    if not outline: return spr
    st = m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(1.2))
    base = Image.new("RGBA", m.size, (122, 12, 18, 0)); base.putalpha(st.point(lambda v: int(min(255, v * 1.6) * .9)))
    base.alpha_composite(spr); return base
def pill_sprite(w, h, bg, pad=70, r=None):
    return clay(rrect(w, h, r or h // 2, pad), bg, d=max(5, int(min(w, h) * .045)), sh_off=(0, 16), sh_blur=15)

# ---------------------------------------------------------------- paper background
def periodic_band(hh, draw_fn, seed):
    L = Image.new("RGBA", (2160, hh), (0, 0, 0, 0)); rng = np.random.default_rng(seed); draw_fn(ImageDraw.Draw(L), rng); return L
def with_shadow(L, off=(0, 10), r=9, a=.38, up=False):
    al = L.getchannel("A"); sh = blur(ImageChops.offset(al, off[0], off[1]), r).point(lambda v: int(v * a))
    base = Image.new("RGBA", L.size, NAVY + (0,)); base.putalpha(sh); base.alpha_composite(L); return base
def cloud_draw(col, n, ymin, ymax, smin, smax):
    def fn(d, rng):
        for _ in range(n):
            cx = rng.uniform(0, 1080); cy = rng.uniform(ymin, ymax); s = rng.uniform(smin, smax)
            for ox in (-1080, 0, 1080):
                x = cx + ox
                d.rounded_rectangle((x - 150 * s, cy, x + 150 * s, cy + 56 * s), radius=28 * s, fill=col)
                for dx, dy, rr in ((-70, 6, 50), (-5, -18, 68), (68, 4, 48), (-115, 20, 34), (118, 22, 32)):
                    d.ellipse((x + (dx - rr) * s, cy + (dy - rr + 30) * s, x + (dx + rr) * s, cy + (dy + rr + 30) * s), fill=col)
    return fn
def wavy(base, amps, x):
    y = base
    for k, a, ph in amps: y = y + a * np.sin(2 * np.pi * k * x / 1080 + ph)
    return y
def hills_draw(col, base, amps):
    def fn(d, rng):
        x = np.arange(0, 2161, 8); y = wavy(base, amps, x)
        d.polygon([(0, 1200)] + list(zip(x, y)) + [(2160, 1200)], fill=col)
    return fn
def torn_draw(col, base, amps, th):
    def fn(d, rng):
        x = np.arange(0, 2161, 12); j = rng.uniform(-7, 7, 91); j = np.tile(j[:90], 3)[:len(x)]
        y = wavy(base, amps, x); top = y - th + j
        d.polygon(list(zip(x, top)) + list(zip(x[::-1], y[::-1] + 2)), fill=col)
    return fn
BANDY = {}
def build_layers():
    L = []
    L.append(("farc", 180, 640, 16, with_shadow(periodic_band(640, cloud_draw((226, 241, 251, 255), 5, 120, 420, .8, 1.15), 3), (0, 14), 12, .25)))
    L.append(("midc", 520, 640, 34, with_shadow(periodic_band(640, cloud_draw(CLOUD + (255,), 4, 150, 420, .9, 1.4), 8), (0, 18), 14, .30)))
    amps_f = [(2, 34, .6), (5, 14, 2.0)]; amps_n = [(3, 20, 1.3), (7, 6, 0.4)]
    L.append(("farh", 1300, 600, 10, with_shadow(periodic_band(600, hills_draw((31, 86, 130, 255), 110, amps_f), 1), (0, -10), 12, .35)))
    L.append(("nearh", 1360, 600, 24, None))
    nb = periodic_band(600, lambda d, rng: (torn_draw(CLOUD + (255,), 100, amps_n, 30)(d, rng), hills_draw(NAVY + (255,), 100, amps_n)(d, rng)), 5)
    L[-1] = ("nearh", 1360, 600, 24, with_shadow(nb, (0, -8), 10, .35))
    L.append(("frontA", 1640, 300, 14, with_shadow(periodic_band(300, hills_draw((28, 72, 110, 255), 60, [(2, 18, .9), (5, 6, 1.7)]), 11), (0, -8), 10, .35)))
    L.append(("frontB", 1790, 200, 20, with_shadow(periodic_band(200, hills_draw((40, 100, 148, 255), 50, [(3, 12, 2.1), (6, 5, .3)]), 12), (0, -8), 10, .35)))
    return L
LAYERS = build_layers()
def sky():
    y = np.linspace(0, 1, H)[:, None, None]; a = np.array(SKY, np.float32); b = np.array((120, 200, 240), np.float32)
    arr = a * (1 - y * .55) + b * (y * .55); arr = np.broadcast_to(arr, (H, W, 3)).astype(np.uint8)
    return Image.fromarray(np.ascontiguousarray(arr)).convert("RGBA")
SKYIMG = sky()
def background(t):
    img = SKYIMG.copy()
    for _, y0, hh, sp, L in LAYERS:
        off = int((-sp * t) % 1080); put(img, L.crop((off, 0, off + 1080, hh)), 0, y0)
    return img

# ---------------------------------------------------------------- characters
BLOBW, BLOBH, PAD = 790, 700, 70
BLOB = clay(rrect(BLOBW, BLOBH, 170), RED, d=16, sh_off=(0, 26), sh_blur=26)
def face(a, t, mood="talk", look=(1, 0)):
    ss = 2; fw, fh = 700, 300; L = Image.new("RGBA", (fw * ss, fh * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    cx = fw // 2 * ss; blink = 1 - max(0, 1 - abs(((t * 1.0) % 3.1) - 2.8) / .12) if (t % 3.1) > 2.6 else 1
    for sx in (-1, 1):
        ex = cx + sx * 135 * ss; ey = 95 * ss
        if mood == "happy":
            d.arc((ex - 44 * ss, ey - 22 * ss, ex + 44 * ss, ey + 40 * ss), 200, 340, fill=CLOUD + (255,), width=14 * ss)
        else:
            eh = 50 * ss * max(.12, blink)
            d.ellipse((ex - 40 * ss, ey - eh, ex + 40 * ss, ey + eh), fill=CLOUD + (255,))
            px = ex + look[0] * 10 * ss; py = ey + look[1] * 8 * ss; pr = 22 * ss; ph = min(pr, eh * .8)
            d.ellipse((px - pr, py - ph, px + pr, py + ph), fill=NAVY + (255,))
            if blink > .5: d.ellipse((px - 4 * ss, py - 12 * ss, px + 6 * ss, py - 2 * ss), fill=CLOUD + (255,))
        d.ellipse((cx + sx * 232 * ss - 34 * ss, 175 * ss, cx + sx * 232 * ss + 34 * ss, 175 * ss + 40 * ss), fill=(255, 150, 150, 120))
    my = 190 * ss
    if mood == "happy":
        d.pieslice((cx - 90 * ss, my - 50 * ss, cx + 90 * ss, my + 80 * ss), 0, 180, fill=NAVY + (255,))
        d.pieslice((cx - 50 * ss, my + 10 * ss, cx + 50 * ss, my + 70 * ss), 0, 180, fill=(235, 110, 120, 255))
    else:
        hgt = (14 + 62 * a) * ss; wd = (66 + 20 * a) * ss
        d.ellipse((cx - wd, my, cx + wd, my + hgt), fill=NAVY + (255,))
        if a > .25: d.ellipse((cx - wd * .55, my + hgt * .52, cx + wd * .55, my + hgt * .98), fill=(235, 110, 120, 255))
    return L.resize((fw, fh), Image.LANCZOS)
HOOK_TY = 244; HOOK_PITCH = 110
HOOKL = [txt_clay("나 put in", 112), txt_clay("jeopardy야", 112)]
def blob_sprite(a, t, mood="talk", with_text=False, look=(1, 0)):
    bs = BLOB.copy(); bs.alpha_composite(face(a, t, mood, look), (PAD + (BLOBW - 700) // 2, PAD + 22))
    if with_text:
        for i, hs in enumerate(HOOKL): bs.alpha_composite(hs, (PAD + (BLOBW - hs.width) // 2 - 0 + 0, PAD + HOOK_TY + i * HOOK_PITCH))
    return bs
def build_balloon():
    BWc, BHc = 560, 600
    mb = mask_draw(BWc - 140, BHc - 140, lambda d, p, s: (d.ellipse((p + 70 * s, p, p + 350 * s, p + 320 * s), fill=255), d.polygon([(p + 210 * s, p + 312 * s), (p + 188 * s, p + 345 * s), (p + 232 * s, p + 345 * s)], fill=255)), 70)
    bal = clay(mb, NAVY, d=14, sh_off=(0, 18), sh_blur=18, sh_alpha=.35, hi=.8)
    band = ImageChops.multiply(mb, mask_draw(BWc - 140, BHc - 140, lambda d, p, s: d.rectangle((p, p + 150 * s, p + 500 * s, p + 205 * s), fill=255), 70))
    bal.alpha_composite(clay(band, CLOUD, d=8, shadow=False, hi=.4))
    d = ImageDraw.Draw(bal); pts = [(280 + 14 * math.sin(i / 8 * math.pi * 1.5), 410 + i * 14) for i in range(9)]
    d.line(pts, fill=NAVY + (255,), width=6, joint="curve")
    return bal, (280, 522)
BAL, BAL_ANCH = build_balloon()
def draw_balloon(img, ax, ay, scale, t, wind=1.0):
    ang = (7 * math.sin(t * 2.3) + 5 * math.sin(t * 5.1 + 1)) * wind - 3 * wind
    rot = BAL.rotate(ang, resample=Image.BICUBIC, center=BAL_ANCH)
    if scale != 1: rot = scaled(rot, scale)
    put(img, rot, ax - BAL_ANCH[0] * scale, ay - BAL_ANCH[1] * scale)
def draw_blob(img, cx, ybot, scale, a, t, mood="talk", with_text=False, pop=1.0, look=(1, 0), dx=0):
    bs = blob_sprite(a, t, mood, with_text, look)
    sq = 1 + .03 * math.sin(t * 3.0) + .05 * a; sy = scale * pop * (1 - .07 * a + .01 * math.sin(t * 3)); sx = scale * pop * sq
    s = scaled(bs, sx, sy)
    put(img, s, cx - s.width / 2 + dx, ybot + PAD * sy - s.height)
    return ybot - BLOBH * sy
CLOUDB = clay(rrect(400, 100, 50), CLOUD, d=8, sh_off=(0, 16), sh_blur=16)
_c = CLOUDB.copy()
def make_bird_cloud():
    m = mask_draw(440, 130, lambda d, p, s: (d.rounded_rectangle((p, p + 40 * s, p + 440 * s, p + 130 * s), radius=45 * s, fill=255),
        d.ellipse((p + 60 * s, p, p + 220 * s, p + 110 * s), fill=255), d.ellipse((p + 170 * s, p - 14 * s, p + 340 * s, p + 100 * s), fill=255),
        d.ellipse((p + 300 * s, p + 20 * s, p + 420 * s, p + 110 * s), fill=255)), 70)
    return clay(m, CLOUD, d=9, sh_off=(0, 18), sh_blur=18)
BIRDCLOUD = make_bird_cloud()
BENV = bird.envelope(MP3, FPS, NF)
def draw_bird(img, i, t):
    cx = 720; bob = 4 * math.sin(t * 2.2); cy0 = 1400 + 6 * math.sin(t * 1.3 + 1)
    put(img, BIRDCLOUD, cx - BIRDCLOUD.width / 2, cy0 - 78)
    sh = Image.new("RGBA", (300, 80), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((40, 30, 260, 62), fill=NAVY + (110,))
    put(img, sh.filter(ImageFilter.GaussianBlur(9)), cx - 150, cy0 - 40)
    bird.place(img, float(BENV[min(i, len(BENV) - 1)]), cx, int(cy0 - 4 + bob))

# ---------------------------------------------------------------- stage (paper cutout)
def build_stage():
    S = Image.new("RGBA", (580, 420), (0, 0, 0, 0))
    def add(fn, off=(0, 9), r=6):
        L = Image.new("RGBA", S.size, (0, 0, 0, 0)); fn(ImageDraw.Draw(L)); S.alpha_composite(with_shadow(L, off, r, .42))
    add(lambda d: d.rectangle((60, 90, 520, 340), fill=LBLUE + (255,)))
    add(lambda d: (d.ellipse((235, 120, 345, 230), fill=CLOUD + (255,)), d.rectangle((60, 90, 520, 100), fill=(60, 150, 205, 255))))
    add(lambda d: d.rectangle((40, 330, 540, 385), fill=CLOUD + (255,)))
    add(lambda d: (d.rectangle((190, 245, 260, 335), fill=NAVY + (255,)), d.rectangle((320, 245, 390, 335), fill=NAVY + (255,)),
                   [d.ellipse((x - 17, y - 17, x + 17, y + 17), fill=CLOUD + (255,)) for x, y in ((225, 270), (225, 308), (355, 270), (355, 308))]))
    add(lambda d: (d.line((290, 335, 290, 215), fill=NAVY + (255,), width=7), d.ellipse((272, 190, 308, 226), fill=NAVY + (255,))))
    def curt(d):
        for sx in (0, 1):
            x0 = 60 if sx == 0 else 410
            d.polygon([(x0, 80), (x0 + 110, 80), (x0 + (60 if sx == 0 else 50), 335), (x0 + (0 if sx == 0 else 0), 335)] if sx == 0 else [(x0, 80), (x0 + 110, 80), (x0 + 110, 335), (x0 + 50, 335)], fill=RED + (255,))
            for k in range(1, 4): d.line((x0 + k * 26, 90, x0 + k * 20 + (8 if sx else 0), 330), fill=DRED + (255,), width=4)
    add(curt)
    def roof(d):
        d.rectangle((40, 40, 540, 95), fill=RED2 + (255,))
        for k in range(10): d.pieslice((40 + k * 50, 60, 90 + k * 50, 125), 0, 180, fill=RED2 + (255,))
        for k in range(10): d.polygon([(48 + k * 50, 40), (82 + k * 50, 40), (65 + k * 50, 72)], fill=(CLOUD if k % 2 else (255, 255, 255)) + (255,))
    add(roof)
    return S
STAGE = build_stage()
_a = np.asarray(STAGE).copy(); _a[..., :3] = (_a[..., :3] * .62).astype(np.uint8); STAGE_DARK = Image.fromarray(_a, "RGBA")
STORM = clay(mask_draw(500, 170, lambda d, p, s: (d.rounded_rectangle((p, p + 70 * s, p + 500 * s, p + 170 * s), radius=50 * s, fill=255),
    d.ellipse((p + 40 * s, p + 20 * s, p + 230 * s, p + 140 * s), fill=255), d.ellipse((p + 170 * s, p, p + 360 * s, p + 130 * s), fill=255),
    d.ellipse((p + 300 * s, p + 40 * s, p + 470 * s, p + 140 * s), fill=255)), 70), (82, 112, 140), d=11, sh_off=(0, 18), sh_blur=18)
def draw_stage(img, ov, x, y, t, wet, scale=1.0, storm_y=None, rain=1.0):
    ang = 1.3 * math.sin(t * 17) * rain + .6 * math.sin(t * 3)
    st = Image.blend(STAGE, STAGE_DARK, min(1, wet)).rotate(ang, resample=Image.BICUBIC, center=(290, 380))
    if scale != 1: st = scaled(st, scale)
    put(img, st, x, y)
    # puddle + ripples on stage floor
    d = ImageDraw.Draw(ov); fy = y + 372 * scale; fx = x + 290 * scale
    pw = (60 + 150 * min(1, wet)) * scale
    d.ellipse((fx - pw, fy - 9 * scale, fx + pw, fy + 11 * scale), fill=(77, 176, 232, 210))
    for k in range(3):
        ph = (t * 1.6 + k / 3) % 1; rr = (20 + 120 * ph) * scale
        d.ellipse((fx - rr, fy - rr * .1, fx + rr, fy + rr * .1 + 2), outline=(248, 250, 252, int(200 * (1 - ph) * min(1, rain + .3))), width=3)
    if storm_y is not None:
        put(img, scaled(STORM, scale), x + 40 * scale + 20 * math.sin(t * 1.7), storm_y + 6 * math.sin(t * 2.1))

# ---------------------------------------------------------------- particles
rng = np.random.default_rng(9)
RAIN = dict(x=rng.uniform(-120, 1200, 260), y=rng.uniform(0, H + 120, 260), v=rng.uniform(1500, 2100, 260), l=rng.uniform(42, 78, 260))
LRAIN = dict(x=rng.uniform(0, 1, 90), y=rng.uniform(0, 1, 90), v=rng.uniform(1.1, 1.6, 90))
WIND = [(rng.uniform(250, 1450), rng.uniform(0, 1700), rng.uniform(900, 1500), rng.uniform(200, 420), rng.uniform(0, 6)) for _ in range(18)]
def leaf_sprite(col):
    ss = 3; im = Image.new("RGBA", (110 * ss, 110 * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(10 * ss, 55 * ss), (45 * ss, 20 * ss), (100 * ss, 55 * ss), (45 * ss, 90 * ss)], fill=col + (255,))
    d.line((14 * ss, 55 * ss, 92 * ss, 55 * ss), fill=NAVY + (150,), width=3 * ss)
    im = im.resize((110, 110), Image.LANCZOS); return with_shadow(im, (3, 5), 3, .4)
LEAVES = [(leaf_sprite(c), rng.uniform(-300, 1100), rng.uniform(300, 1450), rng.uniform(380, 720), rng.uniform(0, 6), rng.uniform(-260, 260), rng.uniform(.6, 1.0))
          for c in [RED, CLOUD, LBLUE, DRED, RED2, CLOUD, RED, LBLUE, CLOUD, DRED, RED2, LBLUE]]
CONF = [(rng.uniform(80, 880), rng.uniform(0, .9), rng.uniform(260, 520), rng.uniform(0, 6.3), [RED, CLOUD, LBLUE, NAVY, RED2][k % 5], rng.uniform(-4, 4)) for k in range(46)]
def rain_level(t):
    if t < 8.2: return 0.0
    if t < 8.9: return (t - 8.2) / .7
    if t < 14.6: return 1.0
    if t < 16.0: return max(0.25, 1 - (t - 14.6) / 1.4 * .75)
    return max(0.0, .25 - (t - 16.0) / .5 * .25)
def draw_rain(ov, t, level, local=None):
    if level <= 0: return
    d = ImageDraw.Draw(ov); n = int(len(RAIN["x"]) * level * .85)
    y = (RAIN["y"][:n] + RAIN["v"][:n] * t) % (H + 140) - 70
    for x, yy, l in zip(RAIN["x"][:n], y, RAIN["l"][:n]):
        d.line((x, yy, x - l * .22, yy - l), fill=(248, 250, 252, 150), width=3)
    if local:
        x0, x1, ytop, ybot = local; m = int(len(LRAIN["x"]) * min(1, level))
        yy = ytop + ((LRAIN["y"][:m] + LRAIN["v"][:m] * t * 1.3) % 1) * (ybot - ytop)
        for u, y2 in zip(LRAIN["x"][:m], yy):
            xx = x0 + u * (x1 - x0); d.line((xx, y2, xx - 8, y2 - 34), fill=(235, 246, 253, 210), width=4)
def draw_wind(img, t, alpha):
    if alpha <= 0: return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for y0, x0, sp, ln, ph in WIND[:6]:
        x = (x0 + sp * t) % (W + 900) - 450
        pts = [(x - ln * k / 6, y0 + 14 * math.sin(k * .9 + ph + t * 3)) for k in range(7)]
        d.line(pts, fill=(255, 255, 255, int(110 * alpha)), width=5, joint="curve")
        cx_, cy_ = pts[0]; d.arc((cx_ - 6, cy_ - 22, cx_ + 38, cy_ + 22), 270, 90, fill=(255, 255, 255, int(110 * alpha)), width=4)
    img.alpha_composite(ov)
    for spr, x0, y0, sp, ph, rot, sc in LEAVES[:4]:
        if t > 5.5 and sp * t + x0 > W + 200: continue
        x = (x0 + sp * t) % (W + 500) - 250 if t < 5.4 else x0 + sp * t - 250
        if x > W + 100: continue
        y = y0 + 70 * math.sin(t * 2.6 + ph); r = spr.rotate(rot * t, resample=Image.BICUBIC)
        if sc != 1: r = scaled(r, sc)
        put(img, fade(r, alpha), x, y)
def draw_confetti(ov, t, t0):
    if t < t0: return
    d = ImageDraw.Draw(ov)
    for x0, dl, sp, ph, col, drift in CONF:
        tt = t - t0 - dl * .3
        if tt < 0: continue
        y = 200 + sp * tt; x = x0 + 40 * math.sin(tt * 3 + ph) + drift * tt * 10
        if y > H + 30: continue
        a = tt * 9 + ph; c, s = math.cos(a), math.sin(a)
        pts = [(x + dx * c - dy * s * (.4 + .6 * abs(math.cos(tt * 4 + ph))), y + dx * s + dy * c) for dx, dy in ((-16, -9), (16, -9), (16, 9), (-16, 9))]
        d.polygon(pts, fill=col + (235,))

# ---------------------------------------------------------------- hero image: balloon on one fraying thread (jeopardy)
def build_balloon_big():
    pad = 70; bw, bh = 400, 450; tipy = bh + 40
    def shape(d, p, s):
        d.ellipse((p, p, p + bw * s, p + bh * s), fill=255)
        d.polygon([(p + bw / 2 * s, p + (bh - 10) * s), (p + (bw / 2 - 30) * s, p + tipy * s), (p + (bw / 2 + 30) * s, p + tipy * s)], fill=255)
    mb = mask_draw(bw, tipy, shape, pad)
    def ell(wd):
        return mask_draw(bw, tipy, lambda d, p, s: d.ellipse((p + (bw - wd) / 2 * s, p, p + (bw + wd) / 2 * s, p + bh * s), fill=255), pad)
    bal = clay(mb, RED, d=22, sh_off=(0, 22), sh_blur=22, sh_alpha=.35, hi=.7)
    for wo, wi in ((345, 300), (215, 170)):
        ring = ImageChops.multiply(ImageChops.subtract(ell(wo), ell(wi)), mb)
        bal.alpha_composite(clay(ring, CLOUD, d=5, shadow=False, hi=.3))
    sh = Image.new("RGBA", bal.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((pad + 70, pad + 50, pad + 140, pad + 170), fill=(255, 255, 255, 90))
    bal.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    BIGC = Image.new("RGBA", (1200, 1200), (0, 0, 0, 0)); ox, oy = 600 - (pad + bw // 2), 960 - (pad + tipy)
    BIGC.alpha_composite(bal, (ox, oy)); return BIGC, (600, 960)
BAL2, BAL2_A = build_balloon_big()
def build_post():
    pad = 40; w, h = 120, 240
    pole = mask_draw(w, h, lambda d, p, s: d.rounded_rectangle((p + 45 * s, p + 30 * s, p + 75 * s, p + h * s), radius=10 * s, fill=255), pad)
    base = mask_draw(w, h, lambda d, p, s: d.ellipse((p + 5 * s, p + (h - 20) * s, p + 115 * s, p + (h + 12) * s), fill=255), pad)
    ball = mask_draw(w, h, lambda d, p, s: d.ellipse((p + 30 * s, p, p + 90 * s, p + 60 * s), fill=255), pad)
    spr = clay(base, NAVY, d=6, sh_off=(0, 8), sh_blur=8); spr.alpha_composite(clay(pole, CLOUD, d=7, sh_off=(0, 8), sh_blur=8))
    spr.alpha_composite(clay(ball, RED2, d=8, sh_off=(0, 8), sh_blur=8)); return spr
POST = build_post()
def build_figs():
    out = []
    for k in range(7):
        ss = 4; im = Image.new("RGBA", (40 * ss, 56 * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = NAVY + (255,)
        d.ellipse((13 * ss, 4 * ss, 27 * ss, 18 * ss), fill=c); d.rounded_rectangle((10 * ss, 18 * ss, 30 * ss, 52 * ss), radius=7 * ss, fill=c)
        if k % 3 == 0: d.line((28 * ss, 22 * ss, 36 * ss, 6 * ss), fill=c, width=4 * ss); d.polygon([(36 * ss, 6 * ss), (36 * ss, 14 * ss), (44 * ss - 2, 10 * ss)], fill=RED + (255,)) if False else None
        if k % 3 == 1: d.line((12 * ss, 22 * ss, 4 * ss, 8 * ss), fill=c, width=4 * ss)
        if k % 3 == 2: d.line((28 * ss, 22 * ss, 36 * ss, 8 * ss), fill=c, width=4 * ss); d.line((12 * ss, 22 * ss, 4 * ss, 8 * ss), fill=c, width=4 * ss)
        out.append(im.resize((40, 56), Image.LANCZOS))
    return out
FIGS = build_figs()
def build_warn():
    pad = 40; w, h = 190, 165
    def tri(sc, cx_=95, cy_=0):
        def fn(d, p, s):
            pts = [(95, 4), (186, 158), (4, 158)]; gx = sum(q[0] for q in pts) / 3; gy = sum(q[1] for q in pts) / 3
            d.polygon([(p + (gx + (x - gx) * sc) * s, p + (gy + (y - gy) * sc) * s) for x, y in pts], fill=255)
        return mask_draw(w, h, fn, pad)
    ob = clay(tri(1.08), NAVY, d=7, sh_off=(0, 12), sh_blur=12); ob.alpha_composite(clay(tri(.96), CLOUD, d=5, shadow=False, hi=.4)); ob.alpha_composite(clay(tri(.72), RED, d=5, shadow=False, hi=.4))
    ImageDraw.Draw(ob).text((pad + 95, pad + 108), "!", font=font(92), fill=CLOUD + (255,), anchor="mm"); return ob
WARN = build_warn()
def build_burst():
    ss = 4; n = 9; S = 130; im = Image.new("RGBA", (S * ss, S * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = S * ss / 2
    pts = [(c + (S * ss * (.46 if k % 2 == 0 else .24)) * math.cos(math.pi * k / n), c + (S * ss * (.46 if k % 2 == 0 else .24)) * math.sin(math.pi * k / n)) for k in range(2 * n)]
    d.polygon(pts, fill=CLOUD + (255,), outline=RED + (255,), width=5 * ss)
    zz = [(c - 22 * ss, c - 26 * ss), (c + 4 * ss, c - 6 * ss), (c - 10 * ss, c + 4 * ss), (c + 20 * ss, c + 28 * ss)]
    d.line(zz, fill=NAVY + (255,), width=6 * ss, joint="curve"); return with_shadow(im.resize((S, S), Image.LANCZOS), (0, 6), 5, .4)
BURST = build_burst()
SNAP = pill_sprite(200, 78, CLOUD, r=39); ImageDraw.Draw(SNAP).text((PAD + 100, PAD + 40), "snap?", font=font(46), fill=NAVY + (255,), anchor="mm")

def draw_thread(img, p0, p1, f, t, sag=10):
    (x0, y0), (x1, y1) = p0, p1; pad = 50
    bx0, by0 = int(min(x0, x1)) - pad, int(min(y0, y1)) - pad - 20; bx1, by1 = int(max(x0, x1)) + pad, int(max(y0, y1)) + pad + 20
    w, h = bx1 - bx0, by1 - by0; S = 3; d = ImageDraw.Draw(layer := Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)))
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); T = (dx / L, dy / L); Nn = (-T[1], T[0])
    off = sag * (1 - .6 * f) + 3 * math.sin(t * 9) * f
    cx_, cy_ = (x0 + x1) / 2 + Nn[0] * off, (y0 + y1) / 2 + Nn[1] * off
    N = 48; pts = [((1 - u) ** 2 * x0 + 2 * (1 - u) * u * cx_ + u * u * x1, (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cy_ + u * u * y1) for u in [k / N for k in range(N + 1)]]
    P = lambda q: ((q[0] - bx0) * S, (q[1] - by0) * S)
    for k in range(N):
        u = (k + .5) / N; wd = max(2.2, 7.5 * (1 - .75 * f * math.exp(-((u - .5) / .13) ** 2)))
        a_, b_ = P(pts[k]), P(pts[k + 1]); d.line(a_ + b_, fill=NAVY + (255,), width=int(wd * S)); r = wd * S / 2
        d.ellipse((b_[0] - r, b_[1] - r, b_[0] + r, b_[1] + r), fill=NAVY + (255,))
    mid = pts[N // 2]
    for j in range(5):
        o = (j - 2) * 4.2 * f; wob = 3 * f * math.sin(t * 8 + j * 1.7)
        a_ = P((mid[0] - 26 * T[0] + o * Nn[0], mid[1] - 26 * T[1] + o * Nn[1])); b_ = P((mid[0] + 26 * T[0] + (o + wob) * Nn[0], mid[1] + 26 * T[1] + (o + wob) * Nn[1]))
        d.line(a_ + b_, fill=NAVY + (235,), width=int(1.4 * S))
    put(img, layer.resize((w, h), Image.LANCZOS), bx0, by0); return mid
def draw_streaks(img, t, x0, x1, ys, alpha):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for k, y0 in enumerate(ys):
        u = (t * .55 + k * .31) % 1; ln = 190; x = x0 - 20 + u * (x1 - x0 + ln); al = math.sin(math.pi * u)
        pts = [(x - ln * j / 6, y0 + 9 * math.sin(j * .9 + k + t * 3)) for j in range(7)]; pts = [q for q in pts if x0 <= q[0] <= x1]
        if len(pts) >= 2: d.line(pts, fill=(255, 255, 255, int(110 * al * alpha)), width=5, joint="curve")
    img.alpha_composite(ov)
def draw_pop(img, spr, cx_, cy_, p, extra=1.0, rot=0):
    if p <= 0: return
    s = scaled(spr, max(.15, back(p)) * extra)
    if rot: s = s.rotate(rot, resample=Image.BICUBIC)
    put(img, s, cx_ - s.width / 2, cy_ - s.height / 2)

HG = 1448; POSTX = 290; POSTY = HG - 218
def hero_balloon(img, t, f, a, mood, streak=0.0, snap=0.0, tri=0.0, look=(1, -1)):
    """balloon tethered to a post by one fraying thread; f = fray level 0..1"""
    put(img, POST, POSTX - 100, POSTY - 70)
    for k, fg in enumerate(FIGS):
        put(img, fg, 62 + k * 27, HG - 56 + 4 + 2.5 * abs(math.sin(t * 3 + k * 1.3)) * -1)
    draw_blob(img, 450, HG + 6, .25, a, t, mood=mood, look=look)
    if streak > 0: draw_streaks(img, t, 62, 330, (880, 945, 1010), streak)
    kx = 570 + 16 * f + 6 * f * math.sin(t * 23) + 4 * math.sin(t * 7); ky = 1150 - 10 * f + 5 * f * math.sin(t * 19 + 1)
    mid = draw_thread(img, (POSTX, POSTY), (kx, ky), f, t, sag=10)
    ang = -(20 + 5 * math.sin(t * 2.6) + 4 * f * math.sin(t * 11))
    rot = BAL2.rotate(ang, resample=Image.BICUBIC, center=BAL2_A)
    put(img, rot, kx - BAL2_A[0], ky - BAL2_A[1])
    if tri > 0: draw_pop(img, WARN, 165, 770 + 5 * math.sin(t * 4), tri, 1 + .05 * math.sin(t * 6))
    if snap > 0:
        draw_pop(img, BURST, mid[0], mid[1], snap, 1 + .12 * math.sin(t * 9), 8 * math.sin(t * 7))
        draw_pop(img, SNAP, mid[0] - 150, mid[1] - 80 + 3 * math.sin(t * 3), snap)

STAGEP = Image.new("RGBA", (720, 500), (0, 0, 0, 0)); STAGEP.alpha_composite(STAGE, (60, 20))
STAGEP_D = Image.new("RGBA", (720, 500), (0, 0, 0, 0)); STAGEP_D.alpha_composite(STAGE_DARK, (60, 20))
HRAIN = np.random.default_rng(4); HRX = HRAIN.uniform(0, 1, 30); HRP = HRAIN.uniform(0, 1, 30); HRV = HRAIN.uniform(.7, 1.1, 30)
def hero_hang(img, t, f, wet, rl, tri=0.0, snap=0.0):
    cx = 320 + 10 * math.sin(t * 1.3); by = 4 * math.sin(t * 2.1); A = (cx, 892 + by)
    put(img, scaled(STORM, .9), cx - 288, 745 - 63 + by)
    d = ImageDraw.Draw(img)
    for u, ph, v in list(zip(HRX, HRP, HRV))[:int(30 * rl)]:
        x = 70 + u * 570 + (cx - 320) * .5; y = 900 + ((ph + v * t * .9) % 1) * 500
        d.line((x, y, x - 7, y - 30), fill=(235, 246, 253, 200), width=4)
    th = (3.5 + 3 * f) * math.sin(t * 2.1) + 1.5 * f * math.sin(t * 17)
    L = 153 + 6 * f; R = (A[0] + L * math.sin(math.radians(th)), A[1] + L * math.cos(math.radians(th)))
    st = Image.blend(STAGEP, STAGEP_D, min(1, wet)).rotate(-th, resample=Image.BICUBIC, center=(350, 60))
    # puddle + ripples under the swinging stage
    fx, fy = 320, 1432; pw = 90 + 160 * min(1, wet)
    d.ellipse((fx - pw, fy - 15, fx + pw, fy + 17), fill=(77, 176, 232, 235), outline=(248, 250, 252, 230), width=3)
    for k in range(3):
        ph = (t * 1.2 + k / 3) % 1; rr = (16 + .9 * pw * ph) * 1.0
        d.ellipse((fx - rr, fy - rr * .16, fx + rr, fy + rr * .16 + 2), outline=(248, 250, 252, int(220 * (1 - ph) * min(1, rl + .3))), width=3)
    put(img, st, R[0] - 350, R[1] - 60)
    mid = draw_thread(img, A, R, f, t, sag=4)
    if tri > 0: draw_pop(img, WARN, 735, 985 + 5 * math.sin(t * 4), tri, 1 + .05 * math.sin(t * 6))
    if snap > 0:
        draw_pop(img, BURST, mid[0], mid[1], snap, 1 + .12 * math.sin(t * 9), 8 * math.sin(t * 7))
        draw_pop(img, SNAP, mid[0] + 150, mid[1] - 8 + 3 * math.sin(t * 3), snap)

# ---------------------------------------------------------------- cards
def card_layout(lines, sz, bg, plain, hl_bg, hl_fg, inner_w, line_h, padv=62, padh=50, align="left"):
    """lines: [(words[(idx,text)], is_hl)] ; returns panel sprite, word sprites, pill sprites (panel-relative incl PAD)"""
    ph = padv * 2 + line_h * len(lines); pw = inner_w + 2 * padh
    panel = pill_sprite(pw, ph, bg, r=70); items = []; pills = []
    f = font(sz); sp = f.getlength(" ") + 2
    for li, (wl, hl) in enumerate(lines):
        wds = [f.getlength(t) for _, t in wl]; tot = sum(wds) + sp * (len(wl) - 1)
        x = PAD + padh + (0 if align == "left" else (inner_w - tot) / 2) + (26 if hl else 0); y = PAD + padv + li * line_h
        if hl:
            pwid = int(tot + 52); pl = pill_sprite(pwid, line_h - 14, hl_bg, pad=40, r=(line_h - 14) // 2)
            pills.append((pl, x - 26 - 40, y + 7 - 40, wl[0][0]))
        for (idx, t), wd in zip(wl, wds):
            items.append((txt_flat(t, sz, hl_fg if hl else plain), x - 6, y + (line_h - sz * 1.6) / 2 - 2, idx)); x += wd + sp
    return panel, items, pills
def draw_card(img, now, t0, x, y, lay, bobamp=3, t=0, ghost=False):
    panel, items, pills = lay; p = (now - t0) / .3; s = .88 + .12 * back(p); by = bobamp * math.sin(t * 2 + x)
    ps = scaled(panel, s) if p < 1 else panel
    put(img, ps, x - PAD + (panel.width - ps.width) / 2 + 0, y - PAD + (panel.height - ps.height) / 2 + by)
    for pl, px, py, fi in pills:
        q = (now - wstart(fi) + .03) / .25
        if q <= 0: continue
        sc = back(q); r = scaled(pl, max(.2, sc)); put(img, r, x - PAD + px + (pl.width - r.width) / 2, y - PAD + py + (pl.height - r.height) / 2 + by - 0)
    for spr, px, py, idx in items:
        q = (now - wstart(idx)) / .16
        if q <= 0:
            if ghost: put(img, fade(spr, .3), x - PAD + px, y - PAD + py + by)
            continue
        put(img, fade(spr, q), x - PAD + px, y - PAD + py + by + 14 * (1 - min(1, q)))
# example EN: fit font
def fit_en():
    toks = spec["beats"][2]["on_screen"].split(); base = 15  # first word idx of example_en
    hl = spec["highlight"].split(); hi = next(i for i in range(len(toks)) if [t.strip(".,").lower() for t in toks[i:i + len(hl)]] == [h.lower() for h in hl])
    idxs = [(base + i, t) for i, t in enumerate(toks)]
    plain = idxs[:hi]; hlw = idxs[hi:hi + len(hl)]; rest = idxs[hi + len(hl):]
    # highlight wraps to two lines: "put the outdoor" / "concert in jeopardy."
    h1, h2 = hlw[:3], hlw[3:] + rest
    lines = [(plain, False), (h1, True), (h2, True)]
    for sz in range(76, 50, -2):
        f = font(sz); sp = f.getlength(" ") + 2
        need = max(sum(f.getlength(t) for _, t in l) + sp * (len(l) - 1) + (52 if h else 0) for l, h in lines)
        if need <= 700: break
    return lines, sz
EN_LINES, EN_SZ = fit_en()
HK = [(i, w["t"]) for i, w in enumerate(words[4:10], 4)]
HOOK2 = card_layout([(HK[:2], False), (HK[2:4], False), (HK[4:], False)], 46, CLOUD, NAVY, RED, CLOUD, 350, 64, padv=28, padh=50, align="center")
EN_CARD = card_layout(EN_LINES, EN_SZ, CLOUD, NAVY, RED, CLOUD, 700, int(EN_SZ * 1.72), padv=44)
KO_TOK = spec["beats"][3]["on_screen"].split(); KO0 = 25
KO_WORDS = [(KO0 + i, t) for i, t in enumerate(KO_TOK)]
KO_LINES = [(KO_WORDS[:3], False), (KO_WORDS[3:4], True), (KO_WORDS[4:], False)]
KO_LINES = [(KO_WORDS[:3], False), (KO_WORDS[3:], False)]
def ko_layout():
    # highlight pill on '위태로워질' inside line 2: build manually via two-part line
    sz = 64; lh = 118
    f = font(sz); sp = f.getlength(" ") + 2
    pw_, ph_ = 788, 62 * 2 + lh * 2
    panel = pill_sprite(pw_, ph_, RED, r=70); items = []; pills = []
    rows = [KO_WORDS[:3], KO_WORDS[3:]]
    for li, row in enumerate(rows):
        tot = sum(f.getlength(t) for _, t in row) + sp * (len(row) - 1) + (44 if li == 1 else 0)
        x = PAD + 44 + (700 - tot) / 2; y = PAD + 62 + li * lh
        for k, (idx, t) in enumerate(row):
            hl = li == 1 and k == 0; wd = f.getlength(t)
            if hl:
                pills.append((pill_sprite(int(wd + 44), lh - 22, CLOUD, pad=40, r=(lh - 22) // 2), x - 40, y + 11 - 40, idx)); x += 22
            items.append((txt_flat(t, sz, DRED if hl else CLOUD), x - 6, y + (lh - sz * 1.6) / 2 - 2, idx)); x += wd + sp + (22 if hl else 0)
    return panel, items, pills
KO_CARD = ko_layout()
MEAN_PANEL = pill_sprite(788, 340, CLOUD, r=80)
MEAN_L1 = txt_flat("~을", 124, NAVY); MEAN_L2 = txt_flat("위태롭게 하다", 118, RED)
TERM_CHIP = pill_sprite(360, 150, NAVY, r=60)
_d = ImageDraw.Draw(TERM_CHIP)
for i, t in enumerate(("put ~ in", "jeopardy")):
    f = font(54); _d.text((PAD + 180, PAD + 38 + i * 70), t, font=f, fill=CLOUD + (255,), anchor="mm")
PAY_PANEL = pill_sprite(788, 356, CLOUD, r=80); PAY_SZ = 112; PAY_ROWH = 128
PAY_ROWS = []
for _li, _tx in enumerate(("put ~ in", "jeopardy")):
    _wd = tw(_tx, PAY_SZ); _y = 32 + _li * 152
    PAY_ROWS.append(dict(pill=pill_sprite(int(_wd + 74), PAY_ROWH, RED, pad=40, r=PAY_ROWH // 2), pw=int(_wd + 74), y=_y,
                         t_n=txt_flat(_tx, PAY_SZ, NAVY), t_h=txt_flat(_tx, PAY_SZ, CLOUD)))
HEAD = pill_sprite(470, 64, RED, r=32); ImageDraw.Draw(HEAD).text((PAD + 235, PAD + 32), "NEWS ENGLISH · CNN", font=font(31), fill=CLOUD + (255,), anchor="mm")
BTN = pill_sprite(700, 210, CLOUD, r=105)
def build_btn():
    b = BTN.copy(); d = ImageDraw.Draw(b); ss = 1
    bm = mask_draw(70, 100, lambda dd, p, s: dd.polygon([(p, p), (p + 70 * s, p), (p + 70 * s, p + 100 * s), (p + 35 * s, p + 66 * s), (p, p + 100 * s)], fill=255), 20)
    b.alpha_composite(clay(bm, RED, d=6, sh_off=(0, 6), sh_blur=6, sh_alpha=.3), (PAD + 60 - 20, PAD + 55 - 20))
    d.text((PAD + 420, PAD + 105), "저장해 두기", font=font(86), fill=NAVY + (255,), anchor="mm"); return b
BTN = build_btn()
HANDLE = Image.new("RGBA", (W, 60), (0, 0, 0, 0)); ImageDraw.Draw(HANDLE).text((W // 2, 30), "지나쌤영어  @jina.ssam_english", font=font(34, "Bold"), fill=CLOUD + (255,), anchor="mm")

def beat_idx(t): return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
def mouth_a(i): return float(BENV[min(i, len(BENV) - 1)])
def ease(p): p = min(1, max(0, p)); return p * p * (3 - 2 * p)
PB = next(b for b in WK["beats"] if b["role"] == "payoff"); EXS, EXE, SAVE = PB["expr_start"], PB["expr_end"], PB["save_start"]
JEO_EN = wstart(24); COULD_EN = wstart(18); WIL_KO = wstart(28)
def render(i):
    t = i / FPS; bi = beat_idx(t); t0 = BT[bi]; a = mouth_a(i)
    img = background(t); rl = rain_level(t); role = spec["beats"][bi]["role"]; pp = (t - t0)
    wetv = min(1, max(0, (t - 8.8) / 6.0))
    if role == "hook":
        pop = .82 + .18 * back(t / .3)
        draw_wind(img, t, 1.0 if t < 5 else max(0, 1 - (t - 5) / 1.2))
        by = 1150; look = (math.cos(t * 2), math.sin(t * 1.3) * .5)
        top = by - BLOBH * .9 * pop
        draw_balloon(img, 700 + 6 * math.sin(t * 2.3), top + 14, .5 * pop, t, 1.0 + .5 * math.sin(t * 1.7))
        draw_blob(img, 456, by, .9, a, t, with_text=True, pop=pop, look=look, dx=8 * math.sin(t * 4.1) * (1 if t < 5 else .4))
        draw_card(img, t, -1.0, 40, 1175, HOOK2, t=t, ghost=True)
    elif role == "meaning":
        f = .3 + .6 * min(1, pp / 3.0)
        hero_balloon(img, t, f, a, "talk", streak=min(1, pp / .5), snap=(t - t0 - .5) / .3, tri=(t - t0 - .2) / .3)
        mp = (t - t0) / .35; s_ = .85 + .15 * back(mp); ps = scaled(MEAN_PANEL, s_)
        by = 3 * math.sin(t * 2); put(img, ps, 62 - PAD + (MEAN_PANEL.width - ps.width) / 2, 306 - PAD + (MEAN_PANEL.height - ps.height) / 2 + by)
        for k, spr in enumerate((MEAN_L1, MEAN_L2)):
            q = (t - t0 - .12 - .1 * k) / .18
            if q > 0: put(img, fade(spr, q), 62 + (788 - spr.width) / 2, 306 + 36 + k * 132 + by + 12 * (1 - min(1, q)) - 10)
    elif role in ("example_en", "example_ko"):
        if role == "example_en":
            f = .25 + .3 * min(1, max(0, (t - t0) / (JEO_EN - t0))) + (.25 if t >= JEO_EN else 0)
            hero_hang(img, t, f, wetv, rl, tri=(t - COULD_EN) / .3, snap=(t - JEO_EN) / .3)
            draw_card(img, t, t0, 62, 306, EN_CARD, t=t)
        else:
            f = .8 + .15 * ease((t - WIL_KO) / .7)
            hero_hang(img, t, f, wetv, rl, tri=1.0, snap=1.0)
            draw_card(img, t, t0, 62, 306, KO_CARD, t=t)
    else:
        pop = .55 + .45 * back(pp / .45) if pp < .45 else 1.0
        sh = 1 - .18 * ease((t - SAVE) / .35)
        cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hero_balloon(cv, t, .55, 0.0, "happy", streak=0.0, snap=0.0, tri=min(1, pp / .3))
        sc_ = pop * sh
        if abs(sc_ - 1) < 1e-3: img.alpha_composite(cv)
        else:
            r_ = cv.resize((int(W * sc_), int(H * sc_)), Image.BILINEAR); put(img, r_, 62 - 62 * sc_, HG - HG * sc_)
        mp = pp / .35; s_ = .85 + .15 * back(mp); ps = scaled(PAY_PANEL, s_)
        by = 3 * math.sin(t * 2); put(img, ps, 62 - PAD + (PAY_PANEL.width - ps.width) / 2, 306 - PAD + (PAY_PANEL.height - ps.height) / 2 + by)
        for k, r in enumerate(PAY_ROWS):
            st_ = wstart(31) if k == 0 else wstart(33)
            q_in = (t - st_ + .03) / .2; q_out = 1 - (t - EXE - .05) / .25
            hp = min(q_in, q_out) if t >= st_ - .03 else 0; hp = min(1, hp)
            cxp = 62 + 394; ry = 306 + r["y"] + by
            if hp > 0:
                pl = scaled(r["pill"], max(.2, back(hp)) if q_in < 1 else max(.01, min(1, q_out)))
                put(img, pl, cxp - pl.width / 2, ry + PAY_ROWH / 2 - pl.height / 2)
            ts = r["t_h"] if hp > .5 else r["t_n"]
            put(img, ts, cxp - ts.width / 2, ry + (PAY_ROWH - PAY_SZ * 1.6) / 2 - 2)
        if t >= SAVE:
            bs = 1 + .03 * math.sin((t - SAVE) * 8); sp = scaled(BTN, .7 * (.8 + .2 * back((t - SAVE) / .3)) * bs)
            put(img, sp, 62 + 245 - sp.width / 2, 740 - sp.height / 2)
    put(img, HEAD, 456 - HEAD.width / 2, 256 - HEAD.height / 2)
    draw_bird(img, i, t)
    put(img, HANDLE, 0, 1558)
    return img.convert("RGB")

def text_in_blob_check(margin=30):
    m = np.asarray(BLOB.getchannel("A")); ok = True
    # use blob body mask (alpha of clay incl. shadow is ~mask inside); require alpha==255 over text bbox + margin
    for i, hs in enumerate(HOOKL):
        bb = hs.getchannel("A").point(lambda v: 255 if v > 90 else 0).getbbox()
        x0 = PAD + (BLOBW - hs.width) // 2 + bb[0]; y0 = PAD + HOOK_TY + i * HOOK_PITCH + bb[1]
        x1 = x0 + bb[2] - bb[0]; y1 = y0 + bb[3] - bb[1]
        reg = m[y0 - margin:y1 + margin, x0 - margin:x1 + margin]
        inside = bool((reg >= 250).all())
        # nearest distance to blob edge in native px
        print(f"hook line {i}: bbox ({x0-PAD},{y0-PAD})-({x1-PAD},{y1-PAD}) in blob {BLOBW}x{BLOBH}; margin {margin}px inside mask: {inside}"); ok &= inside
    return ok
def checks():
    print("HOOK TEXT INSIDE BLOB (+30px native, = 25.5px on screen at .85):", text_in_blob_check())
    pairs = [("handle CLOUD/NAVY hill", CLOUD, NAVY), ("hook text CLOUD/blob RED", CLOUD, RED), ("header CLOUD/RED", CLOUD, RED),
             ("example plain NAVY/CLOUD", NAVY, CLOUD), ("example highlight CLOUD/RED", CLOUD, RED), ("meaning RED/CLOUD", RED, CLOUD),
             ("meaning NAVY/CLOUD", NAVY, CLOUD), ("term chip CLOUD/NAVY", CLOUD, NAVY), ("ko text CLOUD/RED", CLOUD, RED), ("ko hl DRED/CLOUD", DRED, CLOUD),
             ("button NAVY/CLOUD", NAVY, CLOUD), ("payoff text NAVY/CLOUD", NAVY, CLOUD), ("payoff hl CLOUD/RED", CLOUD, RED), ("snap tag NAVY/CLOUD", NAVY, CLOUD), ("warn ! CLOUD/RED", CLOUD, RED), ("thread NAVY/sky mid", NAVY, (60, 160, 218)), ("balloon RED/sky mid (graphic)", RED, (60, 160, 218))]
    for n, a, b in pairs: print(f"contrast {n}: {contrast(a, b):.2f}")
    print("EN font", EN_SZ)

if __name__ == "__main__":
    checks()
    if "--frames" in sys.argv:
        for ts in sys.argv[sys.argv.index("--frames") + 1].split(","):
            render(int(round(float(ts) * FPS))).save(f"{FR}/kw3_{RID}_t{ts}.png")
        sys.exit()
    outp = f"{OUT}/kw3_{RID}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", MP3,
           "-map", "0:v", "-map", "1:a", "-af", "apad", "-t", f"{TOTAL:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-threads", "1", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", outp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(NF):
        p.stdin.write(render(i).tobytes())
        if i % 60 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait(); print("done", outp)
