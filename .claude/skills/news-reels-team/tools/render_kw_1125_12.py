#!/usr/bin/env python3
"""kw_12 'so ~ that' (2026-11-25 episode): ISOMETRIC + CLAYMORPHISM + PARTICLES.
Palette card 2: Spruce #17411B / Tennis Yellow #ECF665 / off-white #F6FAE8 / #0B2A10.
Usage: NEWS_ROOT=/home/user/verbgame/content/2026-11-25-cnn python3 render_kw_1125_12.py [--frames t1,t2,...]"""
import os, sys, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-25-cnn")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
RID = "12"; W, H = 1080, 1920; FPS = 30; TAIL = 0.7
OUT = f"{ROOT}/06_keyword_reels"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
MP3 = f"{ROOT}/audio/kw_{RID}.mp3"
FD = "/usr/share/fonts/opentype/noto/NotoSansCJK-"
_fc = {}
def font(sz, w="Black"):
    k = (sz, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}{w}.ttc", sz, index=1)
    return _fc[k]
SPRUCE = (23, 65, 27); YEL = (236, 246, 101); OFF = (246, 250, 232); DARK = (11, 42, 16)
MID = (14, 107, 43); MID2 = (11, 122, 50)

def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

SP = json.load(open(f"{ROOT}/03_script/keyword_scripts.json"))["reels"]
spec = next(x for x in SP if str(x["id"]) == RID) if isinstance(SP, list) else SP[RID]
WK = json.load(open(f"{ROOT}/audio/words_kw.json"))[RID]
words = WK["words"]; BEATS = WK["beats"]; BT = [b["start"] for b in BEATS]
assert [b["role"] for b in BEATS] == [b["role"] for b in spec["beats"]]
FW = {b["role"]: b["first_word_idx"] for b in BEATS}
AUDIO_DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", MP3], capture_output=True, text=True).stdout)
TOTAL = max(AUDIO_DUR, max(w["e"] for w in words)) + TAIL; NF = int(round(TOTAL * FPS))
def ws(i): return words[i]["s"]
def wt(i): return words[i]["t"]
T_SO, T_SMALL, T_THAT = ws(FW["example_en"] + 3), ws(FW["example_en"] + 4), ws(FW["example_en"] + 5)

# ------------------------------------------------------------------ helpers
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
def ease(p):
    p = min(1, max(0, p)); return p * p * (3 - 2 * p)
def scaled(spr, s, sy=None):
    sy = s if sy is None else sy
    return spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * sy))), Image.BILINEAR)
PAD = 70
def mask_draw(w, h, fn, pad=PAD):
    ss = 2; im = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0); d = ImageDraw.Draw(im)
    fn(d, pad * ss, ss); return im.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS)
def rrect(w, h, r, pad=PAD):
    return mask_draw(w, h, lambda d, p, s: d.rounded_rectangle((p, p, p + w * s, p + h * s), radius=r * s, fill=255), pad)
def clay(mask, col, d=None, shadow=True, sh_alpha=.4, sh_off=(0, 16), sh_blur=15, hi=.55, lo=.33):
    from PIL import ImageChops
    bb = mask.getbbox(); bw, bh = bb[2] - bb[0], bb[3] - bb[1]; ms = min(bw, bh)
    d = d or max(4, int(ms * .06)); r = d * 1.2
    m = np.asarray(mask, np.float32) / 255
    a1 = np.asarray(blur(ImageChops.offset(mask, d, d), r), np.float32) / 255
    a2 = np.asarray(blur(ImageChops.offset(mask, -d, -d), r), np.float32) / 255
    pf = np.asarray(blur(mask, max(2, ms * .22)), np.float32) / 255
    hl = m * (1 - a1); sh = m * (1 - a2)
    c = np.array(col, np.float32)[None, None, :]
    rgb = c * (1 + .14 * (pf[..., None] - .55)) + (255 - c) * (hl[..., None] * hi) - c * (sh[..., None] * lo)
    spr = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.asarray(mask, np.float32)]).astype(np.uint8), "RGBA")
    if not shadow: return spr
    sm = blur(ImageChops.offset(mask, sh_off[0], sh_off[1]), sh_blur).point(lambda v: int(v * sh_alpha))
    base = Image.new("RGBA", mask.size, DARK + (0,)); base.putalpha(sm); base.alpha_composite(spr); return base
def pill_sprite(w, h, bg, r=None, d=None):
    return clay(rrect(w, h, r or h // 2), bg, d=d or max(5, int(min(w, h) * .045)))
def txt_flat(t, sz, col, w="Black", pad=6):
    f = font(sz, w); l, tp, r, b = f.getbbox(t)
    im = Image.new("RGBA", (r - l + 2 * pad, int(sz * 1.6)), (0, 0, 0, 0)); ImageDraw.Draw(im).text((pad - l, int(sz * .12)), t, font=f, fill=col + (255,)); return im
def tw(t, sz, w="Black"): return font(sz, w).getlength(t)
def word_pill(t, sz, bg, fg, padx=28, h=None):
    h = h or int(sz * 1.42); w = int(tw(t, sz) + 2 * padx)
    s = pill_sprite(w, h, bg, r=h // 2 - 4)
    ImageDraw.Draw(s).text((PAD + w / 2, PAD + h / 2 + sz * .04), t, font=font(sz), fill=fg + (255,), anchor="mm"); return s

# ------------------------------------------------------------------ background (spruce gradient + drifting iso grid)
GP = 208  # grid period in x (px) -> lines of slope +-tan30
def build_bg():
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array((26, 74, 31), np.float32); bot = np.array((11, 42, 16), np.float32)
    g = np.broadcast_to(top * (1 - y) + bot * y, (H, W, 3)).astype(np.uint8)
    base = Image.fromarray(np.ascontiguousarray(g)).convert("RGBA")
    gw = W + GP * 2; lay = Image.new("RGBA", (gw, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    dd = GP / math.sqrt(3); sl = math.tan(math.radians(30))
    for k in range(-30, 40):
        for s in (1, -1):
            c = k * dd
            d.line((0, c + (0 if s > 0 else 0), gw, c + s * sl * gw), fill=(60, 120, 64, 70), width=2)
    for k in range(-30, 40):  # second family (negative slope) offset
        c = k * dd
        d.line((0, c, gw, c - sl * gw), fill=(60, 120, 64, 70), width=2)
    # remove duplicated first family
    return base, lay
BGBASE, BGGRID = build_bg()
def background(t):
    img = BGBASE.copy(); off = int((t * 26) % GP); put(img, BGGRID.crop((off, 0, off + W, H)), 0, 0); return img

# ------------------------------------------------------------------ ISOMETRIC CLAY ROOM (pre-rendered once)
CW, CH = 1080, 1040; U = 84; C30 = math.cos(math.radians(30)); OX, OY = 540, 470
def P(x, y, z): return (OX + (x - y) * C30 * U, OY + (x + y) * .5 * U - z * U)
def sh_col(c, k): return tuple(int(min(255, max(0, v * k))) for v in c)
def clay_img(im, d=7, shadow=False, sh_off=(0, 18), sh_blur=18, sh_alpha=.4, hi=.42, lo=.28, soften=2.4):
    arr = np.asarray(im, np.float32); a = arr[..., 3] / 255
    pm = np.dstack([arr[..., :3] * a[..., None], arr[..., 3]]).astype(np.uint8)
    bl = np.asarray(Image.fromarray(pm, "RGBA").filter(ImageFilter.GaussianBlur(soften)), np.float32)
    ba = bl[..., 3] / 255; a2 = np.clip((ba - .5) * 3.2 + .5, 0, 1)
    rgb = np.clip(bl[..., :3] / np.maximum(ba, 1e-3)[..., None], 0, 255)
    mask = Image.fromarray((a2 * 255).astype(np.uint8), "L")
    bb = mask.getbbox()
    if bb is None: return im
    ms = min(bb[2] - bb[0], bb[3] - bb[1])
    from PIL import ImageChops
    m = a2
    A1 = np.asarray(blur(ImageChops.offset(mask, d, d), d * 1.2), np.float32) / 255
    A2 = np.asarray(blur(ImageChops.offset(mask, -d, -d), d * 1.2), np.float32) / 255
    pf = np.asarray(blur(mask, max(2, ms * .2)), np.float32) / 255
    hl = m * (1 - A1); sh = m * (1 - A2)
    rr = rgb * (1 + .1 * (pf[..., None] - .55)) + (255 - rgb) * (hl[..., None] * hi) - rgb * (sh[..., None] * lo)
    spr = Image.fromarray(np.dstack([np.clip(rr, 0, 255), a2 * 255]).astype(np.uint8), "RGBA")
    if not shadow: return spr
    sm = blur(ImageChops.offset(mask, sh_off[0], sh_off[1]), sh_blur).point(lambda v: int(v * sh_alpha))
    base = Image.new("RGBA", mask.size, DARK + (0,)); base.putalpha(sm); base.alpha_composite(spr); return base
def obj(faces, **kw):
    im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for pts, col in faces: d.polygon([P(*p) for p in pts], fill=col + (255,))
    return clay_img(im, **kw)
def box(x0, y0, z0, x1, y1, z1, col, k=(1.0, .84, .68)):
    return [([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], sh_col(col, k[0])),
            ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], sh_col(col, k[1])),
            ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], sh_col(col, k[2]))]
def plane_text(base, text, sz, col, org3, ux3, uy3, w_px, h_px):
    """draw text on iso plane: org3 = 3D origin, ux3/uy3 = 3D vectors for the text's x (width) and y (height, downwards)"""
    ti = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0)); ImageDraw.Draw(ti).text((w_px / 2, h_px / 2), text, font=font(sz), fill=col + (255,), anchor="mm")
    o = P(*org3); ex = P(*[org3[i] + ux3[i] for i in range(3)]); ey = P(*[org3[i] + uy3[i] for i in range(3)])
    a = ((ex[0] - o[0]) / w_px, (ex[1] - o[1]) / w_px); b = ((ey[0] - o[0]) / h_px, (ey[1] - o[1]) / h_px)
    det = a[0] * b[1] - a[1] * b[0]
    ia = (b[1] / det, -b[0] / det, -a[1] / det, a[0] / det)  # inverse of [[a0,b0],[a1,b1]]
    c0 = -(ia[0] * o[0] + ia[1] * o[1]); f0 = -(ia[2] * o[0] + ia[3] * o[1])
    out = ti.transform((CW, CH), Image.AFFINE, (ia[0], ia[1], c0, ia[2], ia[3], f0), Image.BICUBIC)
    base.alpha_composite(out)
ZT = lambda s: 4.0 - 1.3 * (s / 6.0)   # sloped (mansard) wall top
def build_room():
    R = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    FLOOR = (222, 233, 178); SLAB = (28, 84, 38)
    LWALL = (236, 246, 101); RWALL = (206, 221, 84); ROOF = (11, 112, 48)
    fl = obj(box(0, 0, -.5, 6, 6, 0, FLOOR, k=(1.0, .62, .48)), d=8, shadow=True, sh_off=(0, 46), sh_blur=40, sh_alpha=.55, hi=.35)
    # recolor slab sides: floor box sides are shade of floor; overpaint with slab green
    side = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); sd = ImageDraw.Draw(side)
    sd.polygon([P(6, 0, -.5), P(6, 6, -.5), P(6, 6, 0), P(6, 0, 0)], fill=sh_col(SLAB, 1.0) + (255,))
    sd.polygon([P(0, 6, -.5), P(6, 6, -.5), P(6, 6, 0), P(0, 6, 0)], fill=sh_col(SLAB, .72) + (255,))
    R.alpha_composite(fl); R.alpha_composite(clay_img(side, d=6))
    # floor planks + ambient shade near walls
    pl = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); pd = ImageDraw.Draw(pl)
    for k in range(1, 12):
        v = k * .5; pd.line([P(v, 0, 0), P(v, 6, 0)], fill=(170, 190, 120, 70), width=2)
    for yv in (0, ):
        pass
    fm = Image.new("L", (CW, CH), 0); ImageDraw.Draw(fm).polygon([P(0, 0, 0), P(6, 0, 0), P(6, 6, 0), P(0, 6, 0)], fill=255)
    pl.putalpha(Image.fromarray((np.asarray(pl.getchannel("A"), np.float32) * np.asarray(fm, np.float32) / 255).astype(np.uint8)))
    R.alpha_composite(pl)
    ao = Image.new("RGBA", (CW, CH), DARK + (0,)); ad = Image.new("L", (CW, CH), 0); adr = ImageDraw.Draw(ad)
    adr.polygon([P(0, 0, 0), P(6, 0, 0), P(6, .8, 0), P(0, .8, 0)], fill=110); adr.polygon([P(0, 0, 0), P(.8, 0, 0), P(.8, 6, 0), P(0, 6, 0)], fill=110)
    ad = blur(ad, 22); ao.putalpha(Image.fromarray((np.asarray(ad, np.float32) * np.asarray(fm, np.float32) / 255).astype(np.uint8))); R.alpha_composite(ao)
    # --- left wall (plane x=0) : inner face + sloped top + end
    TH = .55
    lw = [([(0, 0, 0), (0, 6, 0), (0, 6, ZT(6)), (0, 0, ZT(0))], LWALL),
          ([(0, 0, ZT(0)), (0, 6, ZT(6)), (-TH, 6, ZT(6)), (-TH, -TH, ZT(0))], ROOF),
          ([(0, 6, 0), (-TH, 6, 0), (-TH, 6, ZT(6)), (0, 6, ZT(6))], sh_col(LWALL, .72))]
    R.alpha_composite(obj(lw, d=7, hi=.4))
    rw = [([(0, 0, 0), (6, 0, 0), (6, 0, ZT(6)), (0, 0, ZT(0))], RWALL),
          ([(0, 0, ZT(0)), (6, 0, ZT(6)), (6, -TH, ZT(6)), (-TH, -TH, ZT(0))], sh_col(ROOF, 1.12)),
          ([(6, 0, 0), (6, -TH, 0), (6, -TH, ZT(6)), (6, 0, ZT(6))], sh_col(RWALL, .74))]
    R.alpha_composite(obj(rw, d=7, hi=.4))
    # roof trim bands (inner faces) + tile lines
    trim = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); td = ImageDraw.Draw(trim)
    td.polygon([P(0, 0, ZT(0) - .55), P(6, 0, ZT(6) - .55), P(6, 0, ZT(6)), P(0, 0, ZT(0))], fill=sh_col(ROOF, 1.0) + (255,))
    td.polygon([P(0, 0, ZT(0) - .55), P(0, 6, ZT(6) - .55), P(0, 6, ZT(6)), P(0, 0, ZT(0))], fill=sh_col(ROOF, .86) + (255,))
    R.alpha_composite(clay_img(trim, d=5, hi=.35))
    tl = ImageDraw.Draw(R)
    for k in range(1, 24):
        s = k * 6 / 24
        tl.line([P(s, 0, ZT(s) - .55), P(s, 0, ZT(s))], fill=(8, 80, 34, 150), width=2)
        tl.line([P(0, s, ZT(s) - .55), P(0, s, ZT(s))], fill=(8, 80, 34, 150), width=2)
    for k in range(1, 20):  # top slate lines
        s = k * 6 / 20
        tl.line([P(s, 0, ZT(s)), P(s, -TH, ZT(s))], fill=(8, 80, 34, 160), width=2)
        tl.line([P(0, s, ZT(s)), P(-TH, s, ZT(s))], fill=(8, 80, 34, 160), width=2)
    # skylight in right wall band
    x0, x1 = 2.35, 4.35; zb = 1.55
    fr = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); fd = ImageDraw.Draw(fr)
    fd.polygon([P(x0 - .14, 0, zb - .14), P(x1 + .14, 0, zb - .14), P(x1 + .14, 0, ZT(x1) - .62 + .14), P(x0 - .14, 0, ZT(x0) - .62 + .14)], fill=OFF + (255,))
    R.alpha_composite(clay_img(fr, d=5, shadow=True, sh_off=(0, 8), sh_blur=8, sh_alpha=.35))
    pn = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); pdw = ImageDraw.Draw(pn)
    quad = [P(x0, 0, zb), P(x1, 0, zb), P(x1, 0, ZT(x1) - .62), P(x0, 0, ZT(x0) - .62)]
    pdw.polygon(quad, fill=(18, 60, 70, 255))
    gm = Image.new("L", (CW, CH), 0); ImageDraw.Draw(gm).polygon(quad, fill=255)
    gy = np.linspace(0, 1, CH)[:, None]; sky = np.zeros((CH, CW, 3), np.float32)
    ytop = min(q[1] for q in quad); ybot = max(q[1] for q in quad); gg = np.clip((np.arange(CH) - ytop) / (ybot - ytop), 0, 1)[:, None, None]
    sky[:] = (np.array((16, 52, 66), np.float32) * (1 - gg) + np.array((70, 150, 120), np.float32) * gg)
    sk = Image.fromarray(np.dstack([sky, np.asarray(gm, np.float32)]).astype(np.uint8), "RGBA"); R.alpha_composite(sk)
    sd2 = ImageDraw.Draw(R)
    sx, sy = P(3.0, 0, 2.0)
    sd2.ellipse((sx - 15, sy - 15, sx + 15, sy + 15), fill=(246, 250, 232, 255))
    for (a, b) in ((3.9, 2.3), (2.7, 2.55), (3.55, 1.85)):
        qx, qy = P(a, 0, b); sd2.ellipse((qx - 4, qy - 4, qx + 4, qy + 4), fill=YEL + (255,))
    mxs = [P(x0 + (x1 - x0) / 2, 0, zb), P(x0 + (x1 - x0) / 2, 0, ZT(x0 + 1) - .62)]
    sd2.line([P(x0 + (x1 - x0) / 2, 0, zb), P(x0 + (x1 - x0) / 2, 0, ZT(x0 + 1) - .62)], fill=OFF + (255,), width=7)
    # door on left wall (shared WC)
    y0, y1 = 4.15, 5.45
    dr = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); dd = ImageDraw.Draw(dr)
    dd.polygon([P(0, y0 - .14, 0), P(0, y1 + .14, 0), P(0, y1 + .14, 2.55), P(0, y0 - .14, 2.55)], fill=OFF + (255,))
    R.alpha_composite(clay_img(dr, d=5, shadow=True, sh_off=(0, 8), sh_blur=8, sh_alpha=.3))
    dr2 = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); dd2 = ImageDraw.Draw(dr2)
    dd2.polygon([P(0, y0, 0), P(0, y1, 0), P(0, y1, 2.4), P(0, y0, 2.4)], fill=sh_col(SPRUCE, 1.15) + (255,))
    R.alpha_composite(clay_img(dr2, d=5, hi=.3))
    plane_text(R, "WC", 44, YEL, (0, y0 + .12, 2.25), (0, y1 - y0 - .24, 0), (0, 0, -.5), 130, 60)
    hx, hy = P(0, y1 - .22, 1.1); ImageDraw.Draw(R).ellipse((hx - 7, hy - 7, hx + 7, hy + 7), fill=YEL + (255,))
    # rug
    rg = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); rd = ImageDraw.Draw(rg)
    rd.polygon([P(2.7, 2.2, 0), P(5.3, 2.2, 0), P(5.3, 4.9, 0), P(2.7, 4.9, 0)], fill=MID + (255,))
    rd.polygon([P(2.95, 2.45, 0), P(5.05, 2.45, 0), P(5.05, 4.65, 0), P(2.95, 4.65, 0)], fill=YEL + (255,))
    rd.polygon([P(3.25, 2.75, 0), P(4.75, 2.75, 0), P(4.75, 4.35, 0), P(3.25, 4.35, 0)], fill=MID + (255,))
    R.alpha_composite(clay_img(rg, d=3, hi=.25, lo=.2, soften=1.6))
    # bed (head against left wall, x 0.4..2.3, y 1.0..3.9)
    BEDF = (40, 108, 52)
    parts = [box(.4, .95, 0, 2.3, 3.95, .55, BEDF), box(.4, .9, 0, 2.3, 1.12, 1.75, (30, 86, 40))]
    R.alpha_composite(obj(parts[0] + parts[1], d=8, shadow=True, sh_off=(0, 24), sh_blur=22, sh_alpha=.4))
    R.alpha_composite(obj(box(.5, 1.9, .5, 2.2, 3.85, 1.0, YEL), d=9, hi=.5))
    R.alpha_composite(obj(box(.62, 1.15, .5, 2.08, 1.85, 1.0, OFF), d=8, hi=.5))
    # blanket fold
    bf = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); ImageDraw.Draw(bf).polygon([P(.5, 2.5, 1.0), P(2.2, 2.5, 1.0), P(2.2, 2.75, 1.0), P(.5, 2.75, 1.0)], fill=(205, 218, 70, 255))
    R.alpha_composite(clay_img(bf, d=3, hi=.3, soften=1.5))
    # nightstand + lamp
    R.alpha_composite(obj(box(.4, .25, 0, 1.0, .75, .75, (40, 108, 52)), d=6, shadow=True, sh_off=(0, 14), sh_blur=12, sh_alpha=.4))
    R.alpha_composite(obj(box(.58, .38, .75, .82, .62, 1.0, DARK) + box(.5, .3, 1.0, .9, .7, 1.4, YEL, k=(1.0, .9, .78)), d=4, hi=.5))
    # fairy light cords
    cd = ImageDraw.Draw(R); LB = []
    for k in range(9):
        s = .45 + k * (5.1 / 8); sag = .20 * math.sin(math.pi * ((k % 2) * .5 + .25))
        LB.append(P(s, 0, ZT(s) - .95 + (.0 if k % 2 == 0 else -.14)))
    for k in range(7):
        s = .7 + k * (4.6 / 6); LB.append(P(0, s, ZT(s) - .95 + (.0 if k % 2 == 0 else -.14)))
    pts_r = LB[:9]; pts_l = LB[9:]
    cd.line(pts_r, fill=(20, 60, 30, 255), width=3, joint="curve"); cd.line(pts_l, fill=(20, 60, 30, 255), width=3, joint="curve")
    BULB_POS = LB
    # base room shadow already within floor object; bird anchor on the mattress
    return R, BULB_POS, P(1.35, 2.85, 1.0), P(.65, .5, 1.45)
ROOM_LIT, BULBS, BED_PT, LAMP_PT = build_room()
_a = np.asarray(ROOM_LIT).astype(np.float32); _d = _a.copy(); _d[..., :3] = _d[..., :3] * np.array((.66, .78, .80), np.float32)
ROOM_DIM = Image.fromarray(_d.astype(np.uint8), "RGBA")
_l = _a.copy(); _l[..., :3] = np.clip(_l[..., :3] * np.array((1.04, 1.0, .9), np.float32), 0, 255)
ROOM_LIT = Image.fromarray(_l.astype(np.uint8), "RGBA")
BENV = bird.envelope(MP3, FPS, NF)
def glow_sprite(sz, col=(255, 226, 120), core=(255, 250, 215)):
    yy, xx = np.mgrid[0:sz, 0:sz].astype(np.float32); r = np.hypot(xx - sz / 2, yy - sz / 2) / (sz / 2)
    a = np.clip(1 - r, 0, 1) ** 2.2; c = np.clip(1 - r * 1.6, 0, 1)[..., None]
    rgb = np.array(col, np.float32) * (1 - c) + np.array(core, np.float32) * c
    return Image.fromarray(np.dstack([np.broadcast_to(rgb, (sz, sz, 3)), a * 255]).astype(np.uint8), "RGBA")
GLOW64 = glow_sprite(64); GLOW256 = glow_sprite(256, (255, 214, 100)); GLOW_BIG = glow_sprite(900, (255, 220, 110), (255, 235, 150))
_gc = {}
def glow(sz):
    sz = int(max(4, sz)); k = sz // 3 * 3 + 3
    if k not in _gc: _gc[k] = GLOW64.resize((k, k), Image.BILINEAR)
    return _gc[k]

# room keyframes: anchor position per beat (sprite centre CW/2,CH/2 maps here)
POS = {"hook": (440, 1085), "term": (456, 1105), "meaning": (456, 1150), "example_en": (456, 1135), "example_ko": (456, 625), "payoff": (456, 462)}
ROLES = [b["role"] for b in BEATS]
def beat_idx(t): return max(i for i, b in enumerate(BT) if b <= t + 1e-6)
PRE = .5
def room_anchor(t):
    if t >= BT[5] - PRE:
        a0, a1 = POS["example_ko"], POS["payoff"]; p = ease((t - (BT[5] - PRE)) / PRE)
        return (a0[0] + (a1[0] - a0[0]) * p, a0[1] + (a1[1] - a0[1]) * p)
    bi = beat_idx(t); cur = POS[ROLES[bi]]
    if bi == 0: return cur
    pv = POS[ROLES[bi - 1]]; p = ease((t - BT[bi]) / .55)
    return (pv[0] + (cur[0] - pv[0]) * p, pv[1] + (cur[1] - pv[1]) * p)
def room_scale(t):
    S = 1.12
    if t < .45: S = 1.12 + .30 * (1 - ease(t / .45))
    ts = BT[1]
    if t > ts: S = 1.12 - .05 * ease((t - ts) / 5.0)
    s0 = S if t < T_SO else 1.07
    if t >= T_SO and t < T_SMALL: S = 1.07 + (.86 - 1.07) * ease((t - T_SO) / .3)
    elif t >= T_SMALL and t < T_THAT: S = .86 + (.68 - .86) * ease((t - T_SMALL) / .3)
    elif t >= T_THAT:
        S = .68 + (.50 - .68) * back((t - T_THAT) / .45)
    if t >= BT[5] - PRE: S = .50 - .14 * ease((t - (BT[5] - PRE)) / PRE)   # payoff: room settles small at top BEFORE the payoff panel appears
    return S
def cozy(t):
    return ease((t - T_THAT) / .9) if t >= T_THAT else 0.0
def render_room(img, t, a, c):
    S = room_scale(t) * (1 + .012 * math.sin(t * 2.2)); th = math.radians(2.3 * math.sin(t * .9) + (3.0 * (1 - ease(t / .6))))
    X, Y = room_anchor(t)
    hot = c
    R = Image.blend(ROOM_DIM, ROOM_LIT, min(1, .12 + .88 * hot)) if hot > .01 else Image.blend(ROOM_DIM, ROOM_LIT, .12)
    # bird on the bed
    tmp = Image.new("RGBA", (360, 300), (0, 0, 0, 0)); bird.place(tmp, float(a), 180, 292)
    bs = .86; tmp = tmp.resize((int(360 * bs), int(300 * bs)), Image.LANCZOS)
    shd = Image.new("RGBA", (300, 70), (0, 0, 0, 0)); ImageDraw.Draw(shd).ellipse((50, 20, 250, 54), fill=DARK + (120,)); shd = blur(shd, 6)
    R = R.copy(); R.alpha_composite(shd, (int(BED_PT[0] - 150), int(BED_PT[1] - 36)))
    R.alpha_composite(tmp, (int(BED_PT[0] - tmp.width / 2), int(BED_PT[1] - tmp.height + 22 + 2 * math.sin(t * 2.4))))
    ow, oh = int(CW * S * 1.12), int(CH * S * 1.12)
    ca, sa = math.cos(th), math.sin(th); icx, icy = CW / 2, CH / 2
    ia, ib, id_, ie = ca / S, -sa / S, sa / S, ca / S
    ocx, ocy = ow / 2, oh / 2
    out = R.transform((ow, oh), Image.AFFINE, (ia, ib, icx - (ia * ocx + ib * ocy), id_, ie, icy - (id_ * ocx + ie * ocy)), Image.BILINEAR)
    # warm halo behind
    if c > .01:
        hs = int(1500 * (.6 + .5 * S)); g = GLOW_BIG.resize((hs, hs), Image.BILINEAR)
        put(img, fade(g, .55 * c), X - hs / 2, Y - hs / 2 + 60)
    put(img, out, X - ow / 2, Y - oh / 2)
    def M(p):
        dx, dy = p[0] - icx, p[1] - icy
        return (X + S * (dx * ca + dy * sa), Y + S * (-dx * sa + dy * ca))
    return M
def draw_lights(img, M, t, c):
    pulse = lambda k: .55 + .45 * math.sin(t * 3.0 + k * 1.7)
    for k, b in enumerate(BULBS):
        x, y = M(b); lvl = .22 + .78 * c
        g = glow(150 * lvl * (.8 + .2 * pulse(k)) * (room_scale(t) + .4)); put(img, fade(g, .35 + .65 * lvl), x - g.width / 2, y - g.height / 2)
        r = max(3, 8 * room_scale(t) * .8)
        ImageDraw.Draw(img).ellipse((x - r, y - r, x + r, y + r), fill=(255, 244, 190, 255))
    if c > .02:
        lx, ly = M(LAMP_PT); g = glow(320 * c * (room_scale(t) + .3)); put(img, fade(g, .8), lx - g.width / 2, ly - g.height / 2)

# ------------------------------------------------------------------ particles (dust motes / fairy lights)
rg_ = np.random.default_rng(12); NP = 96
PX = rg_.uniform(30, 1050, NP); PY0 = rg_.uniform(0, 1900, NP); PV = rg_.uniform(16, 52, NP); PSW = rg_.uniform(10, 42, NP)
PFR = rg_.uniform(.6, 1.7, NP); PPH = rg_.uniform(0, 6.3, NP); PSZ = rg_.uniform(6, 16, NP); PTH = rg_.uniform(0, 1, NP); PTW = rg_.uniform(1.2, 3.4, NP)
def draw_particles(img, t, c, burst=0.0):
    dens = .20 + .80 * c + burst
    for i in range(NP):
        if PTH[i] > dens: continue
        y = (PY0[i] - PV[i] * (1 + 1.4 * c) * t) % 2000 - 40; x = PX[i] + PSW[i] * math.sin(t * PFR[i] + PPH[i])
        tw_ = .45 + .55 * (.5 + .5 * math.sin(t * PTW[i] + PPH[i])); fa = min(1, max(0, (y + 40) / 120, 0)) * min(1, (1960 - y) / 150)
        g = glow(PSZ[i] * (3.2 + 1.8 * c)); put(img, fade(g, tw_ * min(1, .35 + .65 * c) * max(0, fa) * .9), x - g.width / 2, y - g.height / 2)

# ------------------------------------------------------------------ text layouts
def card_rows(rows, sz, line_h, inner_w, panel_col, plain, hl_bg, hl_fg, padv=54, padh=44, hl_extra=26):
    ph = padv * 2 + line_h * len(rows); pw = inner_w + 2 * padh
    panel = pill_sprite(pw, ph, panel_col, r=66); items = []; pills = []
    f = font(sz); sp = f.getlength(" ") + 4
    for li, row in enumerate(rows):
        ex = sum(2 * hl_extra for k, (idx, t, hl) in enumerate(row) if hl and (k == 0 or not row[k - 1][2]))
        tot = sum(f.getlength(t) for _, t, _ in row) + sp * (len(row) - 1) + ex
        x = PAD + padh + (inner_w - tot) / 2; y = PAD + padv + li * line_h
        k = 0
        while k < len(row):
            if row[k][2]:
                j = k
                while j + 1 < len(row) and row[j + 1][2]: j += 1
                grp = row[k:j + 1]; gw = sum(f.getlength(t) for _, t, _ in grp) + sp * (len(grp) - 1) + 2 * hl_extra
                pills.append((pill_sprite(int(gw), line_h - 16, hl_bg, r=(line_h - 16) // 2), x - 2 * PAD, y + 8 - 2 * PAD, grp[0][0])); x += hl_extra
                for idx, t, _ in grp:
                    items.append((txt_flat(t, sz, hl_fg), x - 6, y + (line_h - sz * 1.6) / 2 - 2, idx)); x += f.getlength(t) + sp
                x += hl_extra - sp + sp
                k = j + 1
            else:
                idx, t, _ = row[k]
                items.append((txt_flat(t, sz, plain), x - 6, y + (line_h - sz * 1.6) / 2 - 2, idx)); x += f.getlength(t) + sp; k += 1
    return panel, items, pills, pw, ph
def row_w(row, sz, sp_extra=4, hl_extra=26):
    f = font(sz); sp = f.getlength(" ") + sp_extra
    ex = sum(2 * hl_extra for k, (i, t, h) in enumerate(row) if h and (k == 0 or not row[k - 1][2]))
    return sum(f.getlength(t) for _, t, _ in row) + sp * (len(row) - 1) + ex
def draw_card(img, now, t0, x, y, lay, t=0, ghost=True, ghost_col=.28):
    panel, items, pills, pw, ph = lay; p = (now - t0) / .32; s = .86 + .14 * back(p); by = 3 * math.sin(t * 2 + x)
    ps = scaled(panel, s) if p < 1 else panel
    put(img, ps, x - PAD + (panel.width - ps.width) / 2, y - PAD + (panel.height - ps.height) / 2 + by)
    for pl, px, py, fi in pills:
        q = (now - ws(fi) + .03) / .26
        if q <= 0: continue
        r = scaled(pl, max(.2, back(q))); put(img, r, x + px + (pl.width - r.width) / 2, y + py + (pl.height - r.height) / 2 + by)
    for spr, px, py, idx in items:
        q = (now - ws(idx)) / .16
        if q <= 0:
            if ghost: put(img, fade(spr, ghost_col), x - PAD + px, y - PAD + py + by)
            continue
        put(img, fade(spr, q), x - PAD + px, y - PAD + py + by + 14 * (1 - min(1, q)))

# hook pills
HK0 = FW["hook"]; HK_N = BEATS[0]["n_words"]; HOOK_SZ = 96
HOOK_ROWS = [[0, 1], [2, 3], [4], [5, 6]]
HOOK_BG = [OFF, YEL, OFF, YEL]
HOOK_PILLS = {}
for ri, row in enumerate(HOOK_ROWS):
    for i in row: HOOK_PILLS[i] = word_pill(wt(HK0 + i), HOOK_SZ, HOOK_BG[ri], SPRUCE, padx=26, h=140)
HOOK_POS = {}
for ri, row in enumerate(HOOK_ROWS):
    wds = [HOOK_PILLS[i].width - 2 * PAD for i in row]; gap = 16; tot = sum(wds) + gap * (len(row) - 1)
    assert tot <= 788, (ri, tot)
    x = 456 - tot / 2
    for i, wd in zip(row, wds): HOOK_POS[i] = (x - PAD, 318 + ri * 160 - PAD); x += wd + gap
def draw_hook(img, t):
    for i in range(HK_N):
        spr = HOOK_PILLS[i]; x, y = HOOK_POS[i]; s0 = ws(HK0 + i); q = (t - s0) / .28
        by = 5 * math.sin(t * 2.6 + i * 1.1); sway = 0
        if q < 0:
            put(img, fade(spr, .30), x, y + by); continue
        sc = back(q) * 1.0; r = scaled(spr, max(.4, .85 + .15 * sc) if q < 1 else 1.0, None)
        # little squash-bounce on activation
        if q < 1.0:
            bump = 1 + .16 * math.sin(min(1, q) * math.pi); r = scaled(spr, bump, bump * (1 - .06 * math.sin(min(1, q) * math.pi)))
        put(img, r, x + (spr.width - r.width) / 2, y + (spr.height - r.height) / 2 + by)

# term beat
SO_W, THAT_W, CH_H = 190, 300, 200; TX0 = 62
SO_CH = pill_sprite(SO_W, CH_H, YEL, r=70); ImageDraw.Draw(SO_CH).text((PAD + SO_W / 2, PAD + CH_H / 2 + 4), "so", font=font(112), fill=SPRUCE + (255,), anchor="mm")
THAT_CH = pill_sprite(THAT_W, CH_H, OFF, r=70); ImageDraw.Draw(THAT_CH).text((PAD + THAT_W / 2, PAD + CH_H / 2 + 4), "that", font=font(104), fill=SPRUCE + (255,), anchor="mm")
SLOT = pill_sprite(130, 150, DARK, r=44, d=7); ImageDraw.Draw(SLOT).text((PAD + 65, PAD + 80), "~", font=font(100), fill=YEL + (255,), anchor="mm")
CHY = 345
def ribbon(ov, x0, x1, y, amp, t, ph, thick=28):
    n = 24; pts = [(x0 + (x1 - x0) * k / n, y + amp * math.sin(math.pi * k / n) * math.sin(t * 6 + ph)) for k in range(n + 1)]
    d = ImageDraw.Draw(ov)
    d.line([(px, py + 8) for px, py in pts], fill=DARK + (110,), width=thick + 6, joint="curve")
    d.line(pts, fill=MID + (255,), width=thick, joint="curve")
    d.line([(px, py - thick * .26) for px, py in pts], fill=(70, 170, 100, 255), width=max(3, thick // 4), joint="curve")
def draw_term(img, t, t0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pp = t - t0
    s_so, s_that = ws(FW["term"] + 10), ws(FW["term"] + 11)
    on_so = t >= s_so - .02; on_that = t >= s_that - .02
    def chunk(spr, x, on, s0, ph):
        if on:
            q = (t - s0) / .3; sc = .9 + .1 * back(q) + (.12 * math.sin(min(1, q) * math.pi))
            r = scaled(spr, sc); put(img, r, x - PAD + (spr.width - r.width) / 2, CHY - PAD + (spr.height - r.height) / 2 + 4 * math.sin(t * 2.3 + ph))
        else:
            put(img, fade(spr, .30), x - PAD, CHY - PAD + 4 * math.sin(t * 2.3 + ph))
    chunk(SO_CH, TX0, on_so, s_so, 0)
    xt = 850 - THAT_W; chunk(THAT_CH, xt, on_that, s_that, 1.4)
    cx = (TX0 + SO_W + xt) / 2; yy = CHY + CH_H / 2
    amp1 = 26 * (1 if not on_that else max(0, 1 - (t - s_that) / .6)); amp0 = amp1 * (1 if not on_so else .5) if on_so else 26
    if not on_so: amp1 = 26; amp0 = 26
    ribbon(ov, TX0 + SO_W - 6, cx - 65 + 10, yy, amp0, t, 0); ribbon(ov, cx + 65 - 10, xt + 6, yy, amp1, t, 1.7)
    img.alpha_composite(ov)
    sl = SLOT; pulse = 1 + .05 * math.sin(t * 5 + 1) + (.0 if not on_that else .10 * max(0, 1 - (t - s_that) / .5))
    r = scaled(sl, pulse); put(img, r, cx - sl.width / 2 + (sl.width - r.width) / 2, yy - sl.height / 2 + (sl.height - r.height) / 2 + 3)
    draw_card(img, t, t0, 62, 640, TERM_CAP, t=t)

CAP_W = [(i, wt(i)) for i in range(FW["term"], FW["term"] + 10)]
def _cap():
    rows = [[(i, w, False) for i, w in CAP_W[:3]], [(i, w, False) for i, w in CAP_W[3:8]], [(i, w, False) for i, w in CAP_W[8:]]]
    return card_rows(rows, 46, 74, 700, DARK, OFF, YEL, SPRUCE, padv=34, padh=44)
TERM_CAP = _cap()

# meaning
MN0 = FW["meaning"]
MEAN_PANEL = pill_sprite(788, 450, OFF, r=80)
MEAN_L1A = txt_flat("너무 ", 124, SPRUCE); MEAN_L1B = txt_flat("~해서", 124, MID)
MEAN_L2 = txt_flat("…하다", 130, SPRUCE)
CHIP = pill_sprite(330, 96, YEL, r=48); ImageDraw.Draw(CHIP).text((PAD + 165, PAD + 50), "so ~ that", font=font(52), fill=SPRUCE + (255,), anchor="mm")
def draw_meaning(img, t, t0):
    pp = t - t0; c = scaled(CHIP, .86 + .14 * back(pp / .3)); put(img, c, 456 - c.width / 2, 372 - c.height / 2 + 4 * math.sin(t * 2.1))
    s = .85 + .15 * back(pp / .35); ps = scaled(MEAN_PANEL, s); by = 3 * math.sin(t * 2)
    put(img, ps, 62 - PAD + (MEAN_PANEL.width - ps.width) / 2, 470 - PAD + (MEAN_PANEL.height - ps.height) / 2 + by + 0)
    px = 62 + 394
    # line 1: "너무 ~해서" centered ; line 2: "…하다"
    w1 = MEAN_L1A.width + MEAN_L1B.width - 12; x1 = px - w1 / 2; y1 = 470 + 28 + by
    for spr, dx, i in ((MEAN_L1A, 0, MN0), (MEAN_L1B, MEAN_L1A.width - 12, MN0 + 1)):
        q = (t - ws(i)) / .2
        if q > 0: put(img, fade(spr, q), x1 + dx, y1 + 14 * (1 - min(1, q)))
        else: put(img, fade(spr, .25), x1 + dx, y1)
    q = (t - ws(MN0 + 2)) / .22; y2 = 470 + 212 + by; x2 = px - MEAN_L2.width / 2
    if q > 0:
        r = scaled(MEAN_L2, .8 + .2 * back(q)); put(img, fade(r, min(1, q * 1.5)), px - r.width / 2, y2 + (MEAN_L2.height - r.height) / 2)
    else: put(img, fade(MEAN_L2, .25), x2, y2)

# example EN / KO
EN0 = FW["example_en"]; KO0 = FW["example_ko"]
def fit_en():
    toks = [(EN0 + i, wt(EN0 + i), 3 <= i <= 5) for i in range(9)]
    rows = [toks[:3], toks[3:6], toks[6:]]
    for sz in range(92, 50, -2):
        if max(row_w(r, sz) for r in rows) <= 690: break
    return rows, sz
EN_ROWS, EN_SZ = fit_en()
EN_CARD = card_rows(EN_ROWS, EN_SZ, int(EN_SZ * 1.72), 700, OFF, SPRUCE, YEL, SPRUCE)
KO_TOK = [(KO0 + i, wt(KO0 + i), i in (1, 2)) for i in range(6)]
KO_ROWS = [KO_TOK[:3], KO_TOK[3:5], KO_TOK[5:]]
for KO_SZ in range(72, 44, -2):
    if max(row_w(r, KO_SZ) for r in KO_ROWS) <= 690: break
KO_CARD = card_rows(KO_ROWS, KO_SZ, int(KO_SZ * 1.78), 700, OFF, SPRUCE, YEL, SPRUCE, padv=40)

# payoff: expression (expr_start) -> example 1 (ex1_start) -> example 2 (ex2_start) -> save pill (save_start)
PO0 = FW["payoff"]; PB = BEATS[5]
T_EX1, T_EX2, T_SAVE = PB["ex1_start"], PB["ex2_start"], PB["save_start"]
assert words[PO0]["t"].startswith("so") and words[PO0 + 1]["t"].startswith("that")
assert words[PO0 + 2]["t"] == "It" and ws(PO0 + 2) == T_EX1 and words[PO0 + 10]["t"] == "She" and ws(PO0 + 10) == T_EX2 and ws(PO0 + 21) == T_SAVE
EX1 = PO0 + 2; EX2 = PO0 + 10   # ex1 = 8 words, ex2 = 11 words
PO_SZ = 100; EXP_Y = 640; CARD_Y = 810; CHIP_CY = 1218; BTN_CY = 1372
def build_payoff():
    f = font(PO_SZ); sp = f.getlength(" ") + 10; parts = [("so", PO0), ("~", PO0), ("that", PO0 + 1)]
    wds = [f.getlength(p) for p, _ in parts]; tot = sum(wds) + sp * 2; lh = int(PO_SZ * 1.3); pw = 700 + 88; ph = lh + 30
    panel = pill_sprite(pw, ph, YEL, r=70); items = []; x = PAD + (pw - tot) / 2
    for (p, i), wd in zip(parts, wds):
        items.append((txt_flat(p, PO_SZ, SPRUCE if p != "~" else MID), x - 6, PAD + 15 + (lh - PO_SZ * 1.6) / 2 - 2, i)); x += wd + sp
    return panel, items, [], pw, ph
PAYOFF = build_payoff()
def ex_rows(i0, cuts, hl):
    toks = [(i0 + k, wt(i0 + k), k in hl) for k in range(cuts[-1])]
    return [toks[a:b] for a, b in zip((0,) + cuts[:-1], cuts)]
EX1_ROWS = ex_rows(EX1, (3, 5, 8), {2, 4}); EX2_ROWS = ex_rows(EX2, (4, 7, 11), {2, 4})
for EX_SZ in range(70, 50, -2):
    if max(row_w(r, EX_SZ) for r in EX1_ROWS + EX2_ROWS) <= 690: break
EX_LH = 88
EX1_CARD = card_rows(EX1_ROWS, EX_SZ, EX_LH, 700, OFF, SPRUCE, YEL, SPRUCE, padv=26)
EX2_CARD = card_rows(EX2_ROWS, EX_SZ, EX_LH, 700, OFF, SPRUCE, YEL, SPRUCE, padv=26)
# key images: cause chip -> arrow -> result chip (iconic, wordless)
CHS = 150
def chip(bg, fn):
    s_ = pill_sprite(CHS, CHS, bg, r=46); d = ImageDraw.Draw(s_); fn(d, PAD, PAD, CHS); return s_
def ic_snow(d, x, y, n):
    cx, cy = x + n / 2, y + n / 2
    for k in range(3):
        a = math.radians(90 + 60 * k); dx, dy = math.cos(a) * 48, math.sin(a) * 48
        d.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=SPRUCE + (255,), width=9)
        for sgn in (1, -1):
            bx, by = cx + dx * .62 * sgn, cy + dy * .62 * sgn
            for da in (35, -35):
                b = math.atan2(dy * sgn, dx * sgn) + math.radians(180 + da)
                d.line((bx, by, bx + math.cos(b) * 15, by + math.sin(b) * 15), fill=SPRUCE + (255,), width=7)
def ic_house(d, x, y, n):
    cx = x + n / 2; d.polygon([(cx - 52, y + 76), (cx, y + 28), (cx + 52, y + 76)], fill=SPRUCE + (255,))
    d.rectangle((cx - 38, y + 74, cx + 38, y + 124), fill=SPRUCE + (255,)); d.rounded_rectangle((cx - 12, y + 92, cx + 12, y + 124), radius=5, fill=YEL + (255,))
def ic_batt(d, x, y, n):
    d.rounded_rectangle((x + 26, y + 46, x + 112, y + 104), radius=12, outline=SPRUCE + (255,), width=9); d.rounded_rectangle((x + 114, y + 64, x + 128, y + 86), radius=4, fill=SPRUCE + (255,))
    d.rounded_rectangle((x + 38, y + 58, x + 54, y + 92), radius=4, fill=SPRUCE + (255,))
def ic_sleep(d, x, y, n):
    cx, cy = x + 62, y + 80; d.ellipse((cx - 38, cy - 38, cx + 38, cy + 38), fill=SPRUCE + (255,)); d.ellipse((cx - 16, cy - 52, cx + 56, cy + 22), fill=YEL + (255,))
    d.text((x + 100, y + 92), "z", font=font(48), fill=SPRUCE + (255,)); d.text((x + 116, y + 54), "Z", font=font(40), fill=SPRUCE + (255,))
CH_COLD, CH_HOME = chip(OFF, ic_snow), chip(YEL, ic_house); CH_TIRED, CH_SLEEP = chip(OFF, ic_batt), chip(YEL, ic_sleep)
ARW = mask_draw(120, 70, lambda dd, p, s: dd.polygon([(p, p + 22 * s), (p + 70 * s, p + 22 * s), (p + 70 * s, p), (p + 120 * s, p + 35 * s), (p + 70 * s, p + 70 * s), (p + 70 * s, p + 48 * s), (p, p + 48 * s)], fill=255), 20)
ARROW = clay(ARW, YEL, d=6, sh_off=(0, 6), sh_blur=6, sh_alpha=.3)
SLOTCH = pill_sprite(CHS, CHS, DARK, r=46, d=6)
CH_X = [456 - 235, 456 - 60, 456 + 85]   # left edges: cause, arrow(120 wide), result
def draw_chips(img, t, cause, arrow, result, spr_c, spr_r, t0, t1):
    if t < t0 or t >= t1: return
    by = 3 * math.sin(t * 2.4)
    for x, ts, spr, w in ((CH_X[0], cause, spr_c, CHS), (CH_X[1], arrow, ARROW, 120), (CH_X[2], result, spr_r, CHS)):
        q = (t - ts) / .3
        if x == CH_X[1]:
            if q <= 0: continue
            r = scaled(spr, max(.2, back(q))); put(img, r, x - PAD + (spr.width - 2 * PAD - 0) / 2 - (r.width - spr.width) / 2 + 0 - 0, CHIP_CY - spr.height / 2 + (spr.height - r.height) / 2 + by); continue
        if q <= 0: put(img, fade(SLOTCH, .35), x - PAD, CHIP_CY - SLOTCH.height / 2 + by); continue
        r = scaled(spr, max(.2, back(q))); put(img, r, x - PAD + (spr.width - r.width) / 2, CHIP_CY - spr.height / 2 + (spr.height - r.height) / 2 + by)
def build_btn():
    w, h = 640, 130; b = pill_sprite(w, h, OFF, r=65)
    bm = mask_draw(48, 70, lambda dd, p, s: dd.polygon([(p, p), (p + 48 * s, p), (p + 48 * s, p + 70 * s), (p + 24 * s, p + 46 * s), (p, p + 70 * s)], fill=255), 20)
    b.alpha_composite(clay(bm, MID, d=5, sh_off=(0, 5), sh_blur=5, sh_alpha=.3), (PAD + 60 - 20, PAD + 30 - 20))
    ImageDraw.Draw(b).text((PAD + 370, PAD + 66), "저장해 두기", font=font(70), fill=SPRUCE + (255,), anchor="mm"); return b
BTN = build_btn()
HEAD = pill_sprite(470, 64, YEL, r=32); ImageDraw.Draw(HEAD).text((PAD + 235, PAD + 33), "NEWS ENGLISH · CNN", font=font(31), fill=SPRUCE + (255,), anchor="mm")
HANDLE = Image.new("RGBA", (W, 60), (0, 0, 0, 0)); ImageDraw.Draw(HANDLE).text((W // 2, 30), "지나쌤영어  @jina.ssam_english", font=font(34, "Bold"), fill=OFF + (255,), anchor="mm")

def render(i):
    t = i / FPS; bi = beat_idx(t); t0 = BT[bi]; role = ROLES[bi]; a = float(BENV[min(i, len(BENV) - 1)]); pp = t - t0
    img = background(t); c = cozy(t)
    M = render_room(img, t, a, c); draw_lights(img, M, t, c)
    draw_particles(img, t, c, burst=(.5 * max(0, 1 - (t - T_SAVE) / 1.2) if t >= T_SAVE else 0))
    if role == "hook": draw_hook(img, t)
    elif role == "term": draw_term(img, t, t0)
    elif role == "meaning": draw_meaning(img, t, t0)
    elif role == "example_en": draw_card(img, t, t0, 62, 300, EN_CARD, t=t)
    elif role == "example_ko": draw_card(img, t, t0, 62, 905, KO_CARD, t=t)
    else:
        draw_card(img, t, t0, 62, EXP_Y, PAYOFF, t=t)
        if t >= T_EX2:
            draw_card(img, t, T_EX2, 62, CARD_Y, EX2_CARD, t=t, ghost_col=.22)
            draw_chips(img, t, ws(EX2 + 4), ws(EX2 + 5), ws(EX2 + 7), CH_TIRED, CH_SLEEP, T_EX2, 1e9)
        elif t >= T_EX1:
            draw_card(img, t, T_EX1, 62, CARD_Y, EX1_CARD, t=t, ghost_col=.22)
            draw_chips(img, t, ws(EX1 + 3), ws(EX1 + 4), ws(EX1 + 6), CH_COLD, CH_HOME, T_EX1, T_EX2)
        if t >= T_SAVE:
            q = (t - T_SAVE) / .3; sc = (.88 + .12 * back(q)) * (1 + .03 * math.sin(t * 7))
            b = scaled(BTN, sc); put(img, b, 456 - b.width / 2, BTN_CY - b.height / 2)
    put(img, HEAD, 456 - HEAD.width / 2, 256 - HEAD.height / 2)
    put(img, HANDLE, 0, 1558)
    return img.convert("RGB")

def checks():
    pairs = [("hook text SPRUCE/OFF", SPRUCE, OFF), ("hook text SPRUCE/YEL", SPRUCE, YEL), ("term chunk SPRUCE/YEL", SPRUCE, YEL), ("term slot YEL/DARK", YEL, DARK),
             ("term caption OFF/DARK", OFF, DARK), ("meaning SPRUCE/OFF", SPRUCE, OFF), ("meaning ~해서 MID/OFF", MID, OFF), ("example plain SPRUCE/OFF", SPRUCE, OFF),
             ("example highlight SPRUCE/YEL", SPRUCE, YEL), ("payoff SPRUCE/YEL", SPRUCE, YEL), ("payoff ~ MID/YEL", MID, YEL), ("button SPRUCE/OFF", SPRUCE, OFF),
             ("handle OFF/bg DARK", OFF, DARK), ("handle OFF/bg top", OFF, (26, 74, 31)), ("header SPRUCE/YEL", SPRUCE, YEL)]
    for n, a_, b_ in pairs: print(f"contrast {n}: {contrast(a_, b_):.2f}")
    print("EN font", EN_SZ, "KO font", KO_SZ, "PO font", PO_SZ, "EX font", EX_SZ, "words so/small/that", T_SO, T_SMALL, T_THAT)

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
        if i % 60 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait(); print("done", outp)
