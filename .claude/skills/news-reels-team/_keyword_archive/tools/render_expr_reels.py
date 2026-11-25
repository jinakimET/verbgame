#!/usr/bin/env python3
"""Render per-expression IG reels (1080x1920, 30fps) from voice_full.mp3 + words.json.

Usage: python3 render_expr_reels.py [ids...]   (default: all 12)
Rules: reel-voice-glass-sync visuals (glass panel, highlight box, handle), ig-reel structure
(hook from frame 1 -> term+meaning -> example w/ highlight -> translation -> loop card).
Sync = forced-alignment word times only (audio/words.json). No character, no web images.
"""
import json, math, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = __import__("os").environ.get("NEWS_ROOT","/home/user/verbgame/content/2026-11-23-cnn")
OUT = f"{ROOT}/05_expression_reels"
FR = f"{OUT}/frames"
W, H, FPS = 1080, 1920, 30
HOOK_PAD = 1.5      # silent hook hold before the audio starts
OUTRO = 1.6         # loop card length
FADE, SLIDE = 0.35, 50
# Safe zone: y 230..1440, x <= 850 (right 230 px clear)
PX0, PY0, PX1, PY1 = 60, 500, 850, 1300     # glass panel
CX = (PX0 + PX1) // 2                         # 455: centre for all text
TEXT_W = PX1 - PX0 - 110                      # max text width inside panel (680)
PILL_Y0, PILL_Y1 = 250, 316
HANDLE_TOP = 1588

FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FBOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FMED = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size, index=1)
    return _fc[k]

def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ---------------- data ----------------
J = lambda p: json.load(open(f"{ROOT}/{p}"))
scripts = {r["expr_id"]: r for r in J("03_script/expr_scripts.json")["reels"]}
scenes = {s["expr_id"]: s for s in J("03_script/sync_scenes.json")["scenes"]}
words = {w["id"]: w for w in J("audio/words.json")}
exprs = {e["id"]: e for e in J("01_news/expressions.json")}
cards = {c["card"]: c for c in J("02_bento/cards.json")}

def norm(w):
    return re.sub(r"[^a-z0-9']", "", re.sub(r"\(\d+\)$", "", w.lower()))

def timing(eid):
    """All times absolute in voice_full.mp3 seconds."""
    w = words[eid]; sc = scenes[eid]
    ew = [(norm(a), b, c) for a, b, c in w["eng_words"]]
    segs = w["segments"]
    term_text = sc["lines"][0]["text"]
    n_term = len(term_text.replace("~", " ").split())
    ex = sc["lines"][1]
    ex_tokens = ex["text"].split()
    ex_words = ew[n_term:]
    # sanity: aligned example words must match the sentence prefix
    for i, (a, _, _) in enumerate(ex_words):
        if a != norm(ex_tokens[i]):
            raise RuntimeError(f"{eid}: alignment word mismatch {a} vs {ex_tokens[i]}")
    t_term = ew[0][1]
    t_ex = ex_words[0][1]
    snapped = False
    # snap rule: example start inside first speech segment while a later segment exists
    # -> snap to the later segment's start, but only when that segment is plausibly where
    #    the example begins (< 2.0 s away). Otherwise the alignment is trusted.
    if len(segs) > 2 and t_ex < segs[0][1] and segs[1][0] - t_ex < 2.0:
        t_ex = segs[1][0]; snapped = True
    elif len(segs) > 2 and t_ex < segs[0][1]:
        snapped = None  # rule would apply but target is far: keep alignment
    split = ex.get("split_at")
    t_line2 = None
    if split:
        t_line2 = max(ex_words[split][1], t_ex + 0.4) if split < len(ex_words) else None
    hl = ex["highlight"].split()
    hi = None
    nt = [norm(t) for t in ex_tokens]
    for i in range(len(nt)):
        if nt[i:i+len(hl)] == [norm(x) for x in hl]:
            hi = i; break
    if hi is None:
        raise RuntimeError(f"{eid}: highlight not found")
    t_hl = max(ex_words[hi][1], t_ex) if hi < len(ex_words) else t_ex
    if split and hi >= split and t_line2:
        t_hl = max(t_hl, t_line2)
    return dict(clip0=segs[0][0] - 0.2, clip1=w["kor"][1] + 0.2, t_term=t_term, t_ex=t_ex,
                t_line2=t_line2, t_hl=t_hl, hl_idx=(hi, hi + len(hl)), t_ko=w["kor"][0],
                ko_end=w["kor"][1], snapped=snapped, split=split, ex_tokens=ex_tokens)

# ---------------- drawing helpers ----------------
def text_size(f, s):
    b = f.getbbox(s); return b[2] - b[0], b
def fit_lines(text, path, size, maxw, maxlines=2, minsize=40):
    """wrap text into <= maxlines lines, shrinking until it fits."""
    while size >= minsize:
        f = font(path, size)
        toks = text.split(" ")
        lines, cur = [], ""
        for t in toks:
            cand = (cur + " " + t).strip()
            if text_size(f, cand)[0] <= maxw or not cur:
                cur = cand
            else:
                lines.append(cur); cur = t
        lines.append(cur)
        if len(lines) <= maxlines and all(text_size(f, l)[0] <= maxw for l in lines):
            return f, lines
        size -= 4
    return font(path, minsize), [text]

class El:
    """One element: an RGBA sprite placed at (x,y), appearing at t0 (fade+slide)."""
    def __init__(self, img, x, y, t0):
        self.img, self.x, self.y, self.t0 = img, x, y, t0

def text_sprite(lines, f, color, gap=1.25, box=None, align_center=True):
    """Render lines to an RGBA sprite via alpha mask (no colour mixing)."""
    asc, desc = f.getmetrics(); lh = int((asc + desc) * gap)
    ws = [text_size(f, l)[0] for l in lines]
    sw, sh = max(ws) + 4, lh * (len(lines) - 1) + asc + desc + 4
    mask = Image.new("L", (sw, sh), 0); d = ImageDraw.Draw(mask)
    for i, l in enumerate(lines):
        x = (sw - ws[i]) // 2 if align_center else 0
        d.text((x - text_size(f, l)[1][0], i * lh), l, font=f, fill=255)
    spr = Image.new("RGBA", (sw, sh), color + (0,)); spr.putalpha(mask)
    return spr

def place_center(spr, cy, t0):
    return El(spr, CX - spr.width // 2, int(cy - spr.height / 2), t0)

def stack(sprites_t, cy, gap=34):
    """vertically stack [(sprite, t0)] centred at cy."""
    tot = sum(s.height for s, _ in sprites_t) + gap * (len(sprites_t) - 1)
    y = cy - tot / 2; out = []
    for s, t0 in sprites_t:
        out.append(El(s, CX - s.width // 2, int(y), t0)); y += s.height + gap
    return out

def ease(p):
    return 1 - (1 - p) ** 3

# ---------------- background / chrome per card ----------------
def make_base(card):
    c = card["colors"]; bg = hexrgb(c["background"]); cc = c["cell_C"]
    acc1 = hexrgb(c["cell_A"]["bg"]); acc2 = hexrgb(cc["hl"]); acc3 = hexrgb(c["cell_B"]["bg"])
    img = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(img)
    for (x, y, r, col) in [(160, 380, 360, acc2), (900, 760, 420, acc1), (250, 1500, 460, acc3),
                           (880, 1700, 380, acc2)]:
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(0.55 * a + 0.45 * b) for a, b in zip(col, bg)))
    img = img.filter(ImageFilter.GaussianBlur(140))
    # glass panel: blur 26 + white 10% + dark tint from card cell C for legibility
    region = img.crop((PX0, PY0, PX1, PY1)).filter(ImageFilter.GaussianBlur(26))
    tint = Image.new("RGB", region.size, hexrgb(cc["bg"]))
    region = Image.blend(region, tint, 0.62)
    region = Image.blend(region, Image.new("RGB", region.size, (255, 255, 255)), 0.10)
    m = Image.new("L", region.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, region.width - 1, region.height - 1), 56, fill=255)
    img.paste(region, (PX0, PY0), m)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((PX0, PY0, PX1, PY1), 56, outline=(255, 255, 255, 110), width=3)
    od.rounded_rectangle((PX0 + 4, PY0 + 4, PX1 - 4, PY1 - 4), 52, outline=(255, 255, 255, 36), width=2)
    # pill label
    pf = font(FBOLD, 32); pt = "NEWS ENGLISH · CNN"; tw, tb = text_size(pf, pt)
    pw = tw + 64
    PCX = CX - 20   # nudged left so the pill never touches the bird
    od.rounded_rectangle((PCX - pw // 2, PILL_Y0, PCX + pw // 2, PILL_Y1), 33, fill=hexrgb(c["pill"]["bg"]) + (255,))
    od.text((PCX - tw // 2 - tb[0], (PILL_Y0 + PILL_Y1) // 2 - (tb[1] + tb[3]) // 2), pt, font=pf,
            fill=hexrgb(c["pill"]["text"]) + (255,))
    # handle (top 1588)
    hf = font(FBOLD, 30); ht = "지나쌤영어  @jina.ssam_english"; hw, hb = text_size(hf, ht)
    od.text((CX - hw // 2 - hb[0], HANDLE_TOP - hb[1]), ht, font=hf, fill=hexrgb(c["head_and_handle"]) + (235,))
    img = img.convert("RGBA"); img.alpha_composite(ov)
    return img


# ---------------- talking bird (reel-voice-glass-sync 말하는 캐릭터) ----------------
BIRD_PNG = "/home/user/verbgame/content/assets/bird_sprite.png"
BIRD_CX, BIRD_H = 720, 240           # same in all 12 reels; right edge stays < 850
BIRD_BOTTOM = PY0 + 6                 # sits on the panel's top edge
_bird = {}
def bird_parts():
    if _bird: return _bird
    im = Image.open(BIRD_PNG).convert("RGBA"); a = np.array(im).astype(np.int32)
    R, G, B, A = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    m = np.zeros(R.shape, bool)
    win = (R > 170) & (R - G > 40) & (R - B > 50) & (A > 100)
    m[80:141, 130:236] = win[80:141, 130:236]          # beak only inside the face window
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    mid = (y0 + y1) // 2
    # grow the beak mask by 2 px to catch the soft edge
    mm = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    mm = np.array(mm) > 0
    # fur colour: median of opaque pixels in a ring just around the beak
    ring = np.zeros_like(m); ring[max(0, y0 - 14):y1 + 15, max(0, x0 - 14):x1 + 15] = True
    ring &= ~mm & (A > 200)
    fur = np.median(a[ring][:, :3], axis=0).astype(np.uint8)
    body = a.copy().astype(np.uint8)
    # fill beak area column by column: blend fur just above and just below (keeps fur texture tone)
    ya, yb = max(0, y0 - 6), min(a.shape[0] - 1, y1 + 8)
    for x in range(max(0, x0 - 3), min(a.shape[1], x1 + 4)):
        top_c = a[max(0, ya - 3):ya + 1, x, :3].mean(0); bot_c = a[yb:yb + 4, x, :3].mean(0)
        for y in range(ya, yb + 1):
            if mm[y, x]:
                t = (y - ya) / max(1, yb - ya)
                body[y, x, :3] = np.clip((1 - t) * top_c + t * bot_c, 0, 255)
    body_img = Image.fromarray(body)
    patch = body_img.filter(ImageFilter.GaussianBlur(1.5))
    pm = Image.fromarray((mm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    body_img.paste(patch, (0, 0), pm)
    # beak pieces with soft alpha
    soft = np.array(Image.fromarray((mm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float64) / 255
    beak = a.copy().astype(np.float64); beak[..., 3] = A * soft
    beak_img = Image.fromarray(beak.astype(np.uint8))
    top = beak_img.copy(); top.paste((0, 0, 0, 0), (0, mid, top.width, top.height))
    bot = beak_img.copy(); bot.paste((0, 0, 0, 0), (0, 0, bot.width, mid))
    cols = np.nonzero(m[mid - 1:mid + 2].any(0))[0]
    mouth_x = (int(cols.min()), int(cols.max()))
    _bird.update(mouth_x=mouth_x, body=body_img, top=top, bot=bot, mid=mid, box=(x0, y0, x1, y1), fur=tuple(int(v) for v in fur))
    return _bird

_bird_cache = {}
def bird_sprite(a):
    """a: mouth openness 0..1 (quantised). Returns (sprite, x, y) on the 1080x1920 canvas."""
    q = round(a * 20) / 20
    if q in _bird_cache: return _bird_cache[q]
    P = bird_parts(); x0, y0, x1, y1 = P["box"]; mid = P["mid"]
    open_px = 12 * q
    im = P["body"].copy()
    if q > 0:
        e = int(round(open_px + 6)); mx0, mx1 = P["mouth_x"]
        ImageDraw.Draw(im).rounded_rectangle((mx0 + 3, mid - 3, mx1 - 3, mid - 3 + e), radius=e // 2, fill=(70, 25, 30, 255))
    im.alpha_composite(P["bot"], (0, int(round(open_px))))
    im.alpha_composite(P["top"])
    sc = BIRD_H / im.height
    sx, sy = sc * (1 + 0.015 * q), sc * (1 - 0.025 * q)
    w, h = int(round(im.width * sx)), int(round(im.height * sy))
    spr = im.resize((w, h), Image.LANCZOS)
    res = (spr, int(BIRD_CX - w / 2), BIRD_BOTTOM - h)        # bottom-anchored squash
    _bird_cache[q] = res
    return res

def mouth_env(clip0, dur, total):
    """per-frame mouth openness from this clip's own audio RMS; 0 outside the audio window."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{clip0:.3f}", "-t", f"{dur:.3f}",
                          "-i", f"{ROOT}/audio/voice_full.mp3", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64)
    spf = 8000 / FPS; n = int(len(x) / spf)
    rms = np.array([np.sqrt(np.mean(x[int(i * spf):int((i + 1) * spf)] ** 2)) for i in range(n)])
    ref = np.percentile(rms, 90) or 1.0
    v = np.clip(rms / ref, 0, 1) ** 0.8
    v[v < 0.08] = 0
    env = np.zeros(int(round(total * FPS)) + 2)
    off = int(round(HOOK_PAD * FPS)); prev = 0.0
    for i in range(len(env)):
        j = i - off
        tgt = v[j] if 0 <= j < n else 0.0
        prev = tgt if tgt >= prev else prev * 0.6
        if prev < 0.02: prev = 0.0
        env[i] = prev
    return env

# ---------------- beats ----------------
def chip(label, col, fg):
    f = font(FBOLD, 30); tw, tb = text_size(f, label)
    spr = Image.new("RGBA", (tw + 48, 54), (0, 0, 0, 0)); d = ImageDraw.Draw(spr)
    d.rounded_rectangle((0, 0, tw + 47, 53), 27, fill=col + (255,))
    m = Image.new("L", spr.size, 0); ImageDraw.Draw(m).text((24 - tb[0], 27 - (tb[1] + tb[3]) // 2), label, font=f, fill=255)
    txt = Image.new("RGBA", spr.size, fg + (255,)); txt.putalpha(m)
    spr.alpha_composite(txt); return spr

def wrap_example(tokens, split, hl_idx, f, maxw):
    """Force a break at split_at, then wrap each part to maxw without breaking the highlight.
    Returns list of (part_index, [global token indices])."""
    parts = [list(range(0, split)), list(range(split, len(tokens)))] if split else [list(range(len(tokens)))]
    space = text_size(f, "a a")[0] - text_size(f, "aa")[0]
    out = []
    for pi, idxs in enumerate(parts):
        units, i = [], 0
        while i < len(idxs):
            g = idxs[i]
            if g == hl_idx[0]:
                u = [x for x in idxs if hl_idx[0] <= x < hl_idx[1]]
                uw = sum(text_size(f, tokens[x])[0] for x in u) + space * (len(u) - 1)
                if uw <= maxw: units.append(u)
                else: units.extend([[x] for x in u])   # too wide: let the highlight wrap
                i += len(u)
            else:
                units.append([g]); i += 1
        cur = []
        for u in units:
            cand = cur + u
            wd = sum(text_size(f, tokens[x])[0] for x in cand) + space * (len(cand) - 1)
            if cur and wd > maxw:
                out.append((pi, cur)); cur = list(u)
            else:
                cur = cand
        if cur: out.append((pi, cur))
    return out

def example_sprites(tokens, split, hl_idx, f, fg, hlbg, hlfg, maxw):
    """Return [(part_index, line_sprite, box_or_None)] for the example sentence."""
    wl = wrap_example(tokens, split, hl_idx, f, maxw)
    out = []
    asc, desc = f.getmetrics(); pad = 14; space = text_size(f, "a a")[0] - text_size(f, "aa")[0]
    for pi, gidx in wl:
        lt = [tokens[g] for g in gidx]; base = gidx[0]
        ws = [text_size(f, t)[0] for t in lt]
        inh = [hl_idx[0] <= base + i < hl_idx[1] for i in range(len(lt))]
        extra = [0] * len(lt)   # extra gap so box padding doesn't swallow the word space
        for i in range(len(lt)):
            if inh[i] and i > 0 and not inh[i - 1]: extra[i] += pad
            if inh[i] and i + 1 < len(lt) and not inh[i + 1]: extra[i] += pad
        width = sum(ws) + space * (len(lt) - 1) + sum(extra)
        sh = asc + desc + 24
        sw = width + 3 * pad + 8
        mask = Image.new("L", (sw, sh), 0); d = ImageDraw.Draw(mask)
        hmask = Image.new("L", (sw, sh), 0); hd = ImageDraw.Draw(hmask)
        box = Image.new("L", (sw, sh), 0); bd = ImageDraw.Draw(box)
        x = pad; spans = []
        for i, t in enumerate(lt):
            gi = base + i
            inhl = hl_idx[0] <= gi < hl_idx[1]
            if inhl and i > 0 and not inh[i - 1]: x += pad
            # punctuation after the highlighted last word stays outside the box
            core = t
            if inhl and gi == hl_idx[1] - 1 and t[-1] in ".,!?":
                core = t[:-1]
            if inhl:
                cw = text_size(f, core)[0]
                spans.append([x, x + cw])
                hd.text((x - text_size(f, core)[1][0], 10), core, font=f, fill=255)
                if core != t:
                    d.text((x + cw + pad + 4 - text_size(f, t[-1])[1][0], 10), t[-1], font=f, fill=255)
            else:
                d.text((x - text_size(f, t)[1][0], 10), t, font=f, fill=255)
            x += ws[i] + space
            if inhl and i + 1 < len(lt) and not inh[i + 1]: x += pad
        has_box = bool(spans)
        if has_box:
            x0, x1 = spans[0][0] - pad, spans[-1][1] + pad
            bd.rounded_rectangle((max(0, x0), 4, min(sw - 1, x1), sh - 4), 14, fill=255)
        line = Image.new("RGBA", (sw, sh), fg + (0,)); line.putalpha(mask)
        if has_box:
            bx = Image.new("RGBA", (sw, sh), hlbg + (0,)); bx.putalpha(box)
            # highlighted words: white(fg) before the box appears, hlfg on top of box
            hl_plain = Image.new("RGBA", (sw, sh), fg + (0,)); hl_plain.putalpha(hmask)
            hl_on = Image.new("RGBA", (sw, sh), hlfg + (0,)); hl_on.putalpha(hmask)
            out.append((pi, line, (bx, hl_plain, hl_on)))
        else:
            out.append((pi, line, None))
    return out

def build(eid):
    sc = scripts[eid]; ex = exprs[eid]; tm = timing(eid)
    card = cards[ex["card"]]; c = card["colors"]; cc = c["cell_C"]
    white = hexrgb(cc["term"]); mean = hexrgb(cc["mean"]); dim = hexrgb(cc["ko"])
    hlbg, hlfg = hexrgb(cc["hl"]), hexrgb(cc["hlfg"])
    L = lambda t: HOOK_PAD + (t - tm["clip0"])       # absolute -> local
    audio_len = tm["clip1"] - tm["clip0"]
    b_term = HOOK_PAD
    b_ex = L(tm["t_ex"]) - 0.2
    b_ko = L(tm["t_ko"]) - 0.2
    b_out = HOOK_PAD + audio_len - 0.05
    total = round((b_out + OUTRO) * FPS) / FPS
    beats = []
    cy = (PY0 + PY1) // 2
    # hook
    f, lines = fit_lines(sc["hook_text"], FB, 92, TEXT_W, 2)
    q = chip("오늘의 CNN 표현", hlbg, hlfg)
    beats.append((0.0, stack([(q, 0.0), (text_sprite(lines, f, white), 0.0)], cy, 48), []))
    # term + meaning
    f, lines = fit_lines(sc["term"], FB, 120, TEXT_W, 2, 60)
    fm, ml = fit_lines(sc["meaning_ko"], FBOLD, 64, TEXT_W, 2)
    beats.append((b_term, stack([(chip("표현" if " " in sc["term"] else "단어", hlbg, hlfg), b_term),
                                 (text_sprite(lines, f, white), b_term),
                                 (text_sprite(ml, fm, mean), b_term + 0.25)], cy, 40), []))
    # example
    size = 72
    while True:
        fe = font(FBOLD, size)
        exs = example_sprites(tm["ex_tokens"], tm["split"], tm["hl_idx"], fe, white, hlbg, hlfg, TEXT_W - 30)
        if (len(exs) <= 3 and max(s.width for _, s, _ in exs) <= TEXT_W) or size <= 56:
            break
        size -= 4
    items = [(chip("예문", hlbg, hlfg), b_ex)]
    t_parts = [b_ex, (L(tm["t_line2"]) - 0.1 if tm["t_line2"] else b_ex)]
    for pi, s, _ in exs:
        items.append((s, max(b_ex, t_parts[pi])))
    els = stack(items, cy, 18)
    boxes = []
    for i, (pi, s, bx) in enumerate(exs):
        if bx:
            e = els[i + 1]; boxes.append((bx, e, L(tm["t_hl"]) - 0.05))
    beats.append((b_ex, els, boxes))
    # translation
    fk, kl = fit_lines(exprs[eid]["example_ko"], FB, 72, TEXT_W, 3)
    fs, sl = fit_lines(exprs[eid]["example_en"], FMED, 40, TEXT_W, 2, 30)
    beats.append((b_ko, stack([(chip("해석", hlbg, hlfg), b_ko), (text_sprite(kl, fk, white, 1.3), b_ko),
                               (text_sprite(sl, fs, dim), b_ko + 0.2)], cy, 40), []))
    # loop / outro (explanation line ending in a boxed term -> no period)
    ko, en = [p.strip() for p in sc["loop_text"].split("=")]
    fo, ol = fit_lines(ko, FB, 80, TEXT_W, 2)
    fen, enl = fit_lines(en, FB, 80, TEXT_W - 40, 2, 48)
    ens = text_sprite(enl, fen, hlfg)
    ebox = Image.new("RGBA", (ens.width + 40, ens.height + 24), (0, 0, 0, 0))
    ImageDraw.Draw(ebox).rounded_rectangle((0, 0, ebox.width - 1, ebox.height - 1), 14, fill=hlbg + (255,))
    ebox.alpha_composite(ens, (20, 8))
    outro_txt = [b["text"] for b in sc["beats"] if b["show"] == "outro"][0]
    fsv, svl = fit_lines(outro_txt, FBOLD, 48, TEXT_W, 1)
    beats.append((b_out, stack([(text_sprite(ol, fo, white), b_out),
                                (text_sprite(["="], font(FB, 64), mean), b_out),
                                (ebox, b_out + 0.1),
                                (text_sprite(svl, fsv, mean), b_out + 0.35)], cy, 28), []))
    return dict(eid=eid, tm=tm, beats=beats, total=total, audio_len=audio_len, card=card,
                marks=dict(hook=0.75, term=(b_term + b_ex) / 2, ex=min(L(tm["t_hl"]) + 0.6, b_ko - 0.1),
                           ko=(b_ko + b_out) / 2 + 0.3, outro=b_out + 1.0))

def alpha_mul(img, a):
    if a >= 0.999: return img
    r = img.copy(); r.putalpha(r.getchannel("A").point(lambda v: int(v * a))); return r

def frame(base, R, now, mouth=0.0):
    img = base.copy()
    bs, bx_, by_ = bird_sprite(mouth)
    img.alpha_composite(bs, (bx_, by_))
    cur = [b for b in R["beats"] if b[0] <= now + 1e-6][-1]
    _, els, boxes = cur
    def put(spr, x, y, t0):
        p = (now - t0) / FADE
        if p < 0: return False
        p = min(1, p); e = ease(p)
        img.alpha_composite(alpha_mul(spr, e), (x, int(y + SLIDE * (1 - e))))
        return True
    for e in els:
        put(e.img, e.x, e.y, e.t0)
    for (bx, plain, on), e, th in boxes:
        if now < e.t0: continue
        pe = ease(min(1, (now - e.t0) / FADE)); yy = int(e.y + SLIDE * (1 - pe))
        hb = 0 if now < th else ease(min(1, (now - th) / 0.2))
        if hb < 1: img.alpha_composite(alpha_mul(plain, pe * (1 - hb)), (e.x, yy))
        if hb > 0:
            img.alpha_composite(alpha_mul(bx, pe * hb), (e.x, yy))
            img.alpha_composite(alpha_mul(on, pe * hb), (e.x, yy))
    return img

def render(eid):
    R = build(eid); tm = R["tm"]
    base = make_base(R["card"])
    out = f"{OUT}/expr_{eid}.mp4"
    nfr = int(round(R["total"] * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-ss", f"{tm['clip0']:.3f}", "-t", f"{R['audio_len']:.3f}",
           "-i", f"{ROOT}/audio/voice_full.mp3",
           "-filter_complex", f"[1:a]afade=t=in:d=0.05,afade=t=out:st={R['audio_len']-0.08:.3f}:d=0.08,"
                              f"adelay={int(HOOK_PAD*1000)}:all=1,apad,aformat=channel_layouts=stereo[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", "-threads", "2", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
           "-t", f"{R['total']:.3f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    env = mouth_env(tm["clip0"], R["audio_len"], R["total"])
    for i in range(nfr):
        p.stdin.write(frame(base, R, i / FPS, env[i]).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError(f"ffmpeg failed {eid}")
    os.makedirs(FR, exist_ok=True)
    for k, t in R["marks"].items():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", out, "-frames:v", "1",
                        f"{FR}/expr_{eid}_{k}.png"], check=True)
    info = dict(eid=eid, total=R["total"], snapped=tm["snapped"],
                cues={k: round(v, 2) for k, v in dict(term=HOOK_PAD, ex=R["beats"][2][0], hl=R["beats"][2][2][0][2] if R["beats"][2][2] else None,
                                                     ko=R["beats"][3][0], outro=R["beats"][4][0]).items() if v is not None})
    print(json.dumps(info, ensure_ascii=False), flush=True)
    return info

if __name__ == "__main__":
    ids = sys.argv[1:] or [f"{i:02d}" for i in range(1, 13)]
    for e in ids:
        render(e)
