"""쇼츠 에피소드 → 유튜브 16:9 (1920x1080) 롱폼. 영상에서 뽑지 않고 kit 데이터를 직접 읽음.

사용:  python3 youtube16.py episodes/<이름> frames|audio|video|all

읽는 데이터: timing.py(문장·쉼 시간) · episode_cfg.py(사진·초점) · palette.py · exprs.py ·
            <에피소드>/youtube.json(화면 분할·한글 분할·말풍선) · <에피소드>/voice.mp3 · <에피소드>/photos/
구성: 문장 화면 → 표현 카드(각 3초) → 복습(표현 2개씩 2블록 강조, 마지막 노트 안내)
음성: 원본 voice.mp3 조각만 사용, BGM 없음, 효과음은 쇼츠의 '뿅' 재사용.
"""
import os as _os, sys, json, re, math, subprocess, wave
_HERE = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import timing, episode_cfg, palette as P, exprs
import covers as C

S, W, H, FPS = 2, 1920, 1080, 30
CARD_SEC, STEP_SEC, LAST_A, LAST_B = 3.0, 6.5, 3.0, 5.5
INTER = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
KRB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
KRM = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"   # Medium 대체
HAND = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrechorus-mediumitalic.otf"
EMO_RE = C.EMO_RE

def font(path, size):
    kw = {"index": 1} if path in (KRB, KRM) else {}
    return ImageFont.truetype(path, int(round(size * S)), **kw)

def as_list(x): return [] if not x else (list(x) if isinstance(x, (list, tuple)) else [x])
def scr_cards(s): return as_list(s.get("cards", s.get("card")))
def scr_hls(s): return as_list(s.get("hl"))
NS = len(timing.SENTENCES)

def clean(w): return re.sub(r"[^a-z']", "", w.lower())
def mix(a, b, t): return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

class Cv:
    def __init__(s, bg):
        s.im = bg.copy(); s.d = ImageDraw.Draw(s.im)
    def rr(s, box, r, fill=None, outline=None, width=0):
        s.d.rounded_rectangle([v * S for v in box], r * S, fill=fill, outline=outline, width=int(width * S))
    def text(s, xy, t, f, fill, anchor="la"): s.d.text((xy[0] * S, xy[1] * S), t, font=f, fill=fill, anchor=anchor)
    def tw(s, t, f): return f.getlength(t) / S
    def paste(s, img, xy): s.im.alpha_composite(img, (int(xy[0] * S), int(xy[1] * S)))
    def shadow(s, box, r, blur=22, alpha=70, dy=10):
        sh = Image.new("RGBA", s.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([box[0] * S, (box[1] + dy) * S, box[2] * S, (box[3] + dy) * S], r * S, fill=(40, 30, 10, alpha))
        s.im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur * S)))
        s.d = ImageDraw.Draw(s.im)
    def emo(s, ch, size, xy, rot=0, alpha=1.0):
        e = C.emoji(ch, int(size * S))
        if rot: e = e.rotate(rot, resample=Image.BICUBIC, expand=True)
        if alpha < 1:
            e = e.copy(); e.putalpha(e.getchannel("A").point(lambda v: int(v * alpha)))
        s.paste(e, xy)
    def mixed_w(s, t, f, esz):
        return sum(esz if EMO_RE.fullmatch(p) else s.tw(p, f) for p in EMO_RE.split(t) if p) + 6 * len([p for p in EMO_RE.split(t) if p and EMO_RE.fullmatch(p)])
    def mixed(s, cx, y, t, f, fill, esz, anchor_top=True):
        """가운데 정렬로 이모지 섞어 그리기. y = 텍스트 윗선"""
        total = s.mixed_w(t, f, esz); x = cx - total / 2
        for p in [p for p in EMO_RE.split(t) if p]:
            if EMO_RE.fullmatch(p):
                s.emo(p, esz, (x, y + 4)); x += esz + 6
            else:
                s.text((x, y), p, f, fill); x += s.tw(p, f)
    def done(s): return s.im.resize((W, H), Image.LANCZOS).convert("RGB")

def make_bg():
    im = Image.new("RGBA", (W * S, H * S), P.BG + (255,))
    glow = Image.new("L", (W * S, H * S), 0)
    ImageDraw.Draw(glow).ellipse((300 * S, 250 * S, 1620 * S, 1100 * S), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(160 * S))
    im.paste(Image.new("RGB", (W * S, H * S), P.SUN), (0, 0), glow.point(lambda v: int(v * 0.55)))
    return im
BG = make_bg()

# ---------- 공통 머리 ----------
def photo_thumb(photodir, pkey, w=560, h=264):
    f, fx, fy = episode_cfg.PHOTOS[pkey]
    im = Image.open(_os.path.join(photodir, f)).convert("RGB")
    tw_, th_ = w * S, h * S
    sc = max(tw_ / im.width, th_ / im.height)
    im = im.resize((int(im.width * sc + .5), int(im.height * sc + .5)), Image.LANCZOS)
    x = min(max(fx * im.width - tw_ / 2, 0), im.width - tw_); y = min(max(fy * im.height - th_ / 2, 0), im.height - th_)
    im = im.crop((int(x), int(y), int(x) + tw_, int(y) + th_)).convert("RGBA")
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 28 * S, fill=255)
    im.putalpha(m)
    return im

def header(cv, collected, N, cur, ndots, photodir=None, pkey=None, label=None):
    f = font(HAND, 92); t = "My English Diary"
    cv.text((72, 36), t, f, P.INK)
    w = cv.tw(t, f)
    for k in range(4): cv.d.line(((72 + 28) * S, (156 - k * .5) * S, (72 + w - 10) * S, (146 + k) * S), fill=P.ROSE, width=7 * S)
    fk = font(KRB, 28); txt = f"모은 표현 {collected}/{N}"
    cw = cv.tw(txt, fk) + 98
    cv.rr((72, 190, 72 + cw, 246), 28, fill=P.WHITE, outline=P.INK, width=3)
    cv.emo("💭", 34, (96, 201)); cv.text((142, 197), txt, fk, P.INK)
    for k in range(ndots):
        x, y = 86 + k * 34, 280
        if k < cur: cv.d.ellipse(((x - 8) * S, (y - 8) * S, (x + 8) * S, (y + 8) * S), fill=P.LAV)
        elif k == cur: cv.rr((x - 15, y - 8, x + 15, y + 8), 8, fill=P.INK)
        else: cv.d.ellipse(((x - 8) * S, (y - 8) * S, (x + 8) * S, (y + 8) * S), outline=P.INK_SOFT, width=2 * S)
    if photodir is not None:
        box = (1860 - 560, 44, 1860, 308)
        cv.shadow(box, 28, blur=14, alpha=80, dy=6)
        cv.rr((box[0] - 6, box[1] - 6, box[2] + 6, box[3] + 6), 32, fill=P.WHITE)
        cv.paste(photo_thumb(photodir, pkey), (box[0], box[1]))
    if label:
        fl = font(KRB, 30); lw = cv.tw(label, fl) + 60
        cv.rr((1860 - lw, 130, 1860, 190), 30, fill=P.INK)
        cv.text((1860 - lw / 2, 160), label, fl, P.WHITE, "mm")

# ---------- 문장 화면 ----------
def layout_tokens(cv, lines, f):
    toks = []
    for li, line in enumerate(lines):
        words = line.split(" "); total = cv.tw(line, f); x0 = W / 2 - total / 2
        for k, w in enumerate(words):
            pre = cv.tw(" ".join(words[:k]) + (" " if k else ""), f)
            toks.append(dict(li=li, text=w, clean=clean(w), x0=x0 + pre, x1=x0 + pre + cv.tw(w, f), hl=False))
    return toks

def mark_phrase(toks, phrase):
    key = [clean(w) for w in phrase.split()]
    if not key: return
    cl = [t["clean"] for t in toks]
    for i in range(len(cl) - len(key) + 1):
        if cl[i:i + len(key)] == key:
            for t in toks[i:i + len(key)]: t["hl"] = True
            return
    raise SystemExit("hl phrase not found: " + phrase)

def draw_sentence(cv, scr):
    lines = scr["lines"]; n = len(lines)
    sz = 94
    while True:
        f = font(INTER, sz)
        if max(cv.tw(l, f) for l in lines) <= 1740 or sz <= 70: break
        sz -= 2
    gap = 1.62 * sz
    y1 = 500 if n == 2 else 610
    toks = layout_tokens(cv, lines, f)
    for ph in scr_hls(scr): mark_phrase(toks, ph)
    top = lambda y: y - 0.80 * sz; bot = lambda y: y + 0.22 * sz
    base = [y1 + i * gap for i in range(n)]
    # 형광펜
    for li in range(n):
        seg = [t for t in toks if t["li"] == li and t["hl"]]
        if seg: cv.rr((seg[0]["x0"] - 12, top(base[li]), seg[-1]["x1"] + 12, bot(base[li])), 16, fill=P.MARK)
    for li, line in enumerate(lines):
        cv.text((W / 2 - cv.tw(line, f) / 2, base[li]), line, f, P.INK, "ls")
    # 말풍선
    fb = font(KRM, 30); placed = {"top": [], "bottom": []}
    for word, ko, side in scr.get("bubbles", []):
        cand = [t for t in toks if t["clean"] == clean(word)]
        assert cand, f"bubble word not found: {word}"
        assert not cand[0]["hl"], f"bubble word is highlighted: {word}"
        t = cand[0]; cx = (t["x0"] + t["x1"]) / 2; bw = cv.tw(ko, fb) + 44; bh = 58
        x0 = cx - bw / 2
        for (a, b) in sorted(placed[side]):
            if x0 < b + 14 and x0 + bw > a - 14: x0 = b + 14
        placed[side].append((x0, x0 + bw))
        if side == "top":
            yb = top(base[t["li"]]) - 24 - bh
            tail = [(cx - 10, yb + bh), (cx + 10, yb + bh), (cx, yb + bh + 14)]
        else:
            yb = bot(base[t["li"]]) + 24 + 14
            tail = [(cx - 10, yb), (cx + 10, yb), (cx, yb - 14)]
        cv.rr((x0, yb, x0 + bw, yb + bh), 18, fill=P.WHITE, outline=P.INK_SOFT, width=3)
        cv.d.polygon([(a * S, b * S) for a, b in tail], fill=P.INK_SOFT)
        cv.text((x0 + bw / 2, yb + bh / 2 + 1), ko, fb, P.INK, "mm")
    # 한글 해석 상자
    fk = font(KRB, 46); ko = scr["ko"]; maxw = 1560
    kl = [ko]
    if cv.tw(ko, fk) > maxw:
        words = ko.split(" "); kl = [""]
        for w in words:
            if cv.tw((kl[-1] + " " + w).strip(), fk) > maxw: kl.append(w)
            else: kl[-1] = (kl[-1] + " " + w).strip()
    bw = max(cv.tw(l, fk) for l in kl) + 110; bh = 44 + 66 * len(kl)
    y0 = 810
    cv.shadow((W / 2 - bw / 2, y0, W / 2 + bw / 2, y0 + bh), 34, blur=14, alpha=50, dy=6)
    cv.rr((W / 2 - bw / 2, y0, W / 2 + bw / 2, y0 + bh), 34, fill=P.WHITE)
    for i, l in enumerate(kl): cv.text((W / 2, y0 + 22 + 33 + i * 66), l, fk, P.INK, "mm")

def fit_font(cv, path, text, size, maxw, minsize=24):
    while size > minsize and cv.tw(text, font(path, size)) > maxw: size -= 2
    return font(path, size), size

def chip_sentence(cv, cx, y, text, hl, maxw, size, fill, ink, mark, h=92):
    f, sz = fit_font(cv, INTER, text, size, maxw)
    tw_ = cv.tw(text, f); cw = tw_ + 70
    cv.rr((cx - cw / 2, y, cx + cw / 2, y + h), h / 2, fill=fill)
    toks = text.split(" "); x0 = cx - tw_ / 2; cyl = y + h / 2
    key = [clean(w) for w in hl.split()]
    cl = [clean(w) for w in toks]; hs = None
    for i in range(len(cl) - len(key) + 1):
        if key and cl[i:i + len(key)] == key: hs = (i, i + len(key) - 1); break
    if hs:
        a = x0 + cv.tw(" ".join(toks[:hs[0]]) + (" " if hs[0] else ""), f)
        b = a + cv.tw(" ".join(toks[hs[0]:hs[1] + 1]), f)
        cv.rr((a - 8, cyl - sz * 0.62, b + 8, cyl + sz * 0.62), 12, fill=mark)
    cv.text((x0, cyl), text, f, ink, "lm")

# ---------- 표현 카드 ----------
def card_frame(cfg, k, N, scr, photodir, ci=0):
    em, en, ko = exprs.EXPRS[k]
    cv = Cv(BG); header(cv, k + 1, N, scr["sid"] - 1, NS, photodir, tuple(scr["pkey"]) if len(scr["pkey"]) > 1 else scr["pkey"][0])
    box = (210, 380, 1710, 1000)
    cv.shadow(box, 56, blur=26, alpha=95, dy=14)
    cv.rr(box, 56, fill=P.INK)
    fl = font(KRB, 34); lw = cv.tw("오늘의 표현", fl) + 70
    cv.rr((box[0] + 64, box[1] + 52, box[0] + 64 + lw, box[1] + 112), 30, fill=P.MARK)
    cv.text((box[0] + 64 + lw / 2, box[1] + 83), "오늘의 표현", fl, P.INK, "mm")
    cv.emo(em, 165, (box[2] - 250, box[1] + 14), rot=-14)
    fe, _ = fit_font(cv, INTER, en, 124, 1150)
    cv.text((W / 2, box[1] + 285), en, fe, P.WHITE, "mm")
    fk = font(KRB, 60); cv.text((W / 2, box[1] + 392), ko, fk, P.MARK, "mm")
    text = " ".join(scr["lines"])
    hls = scr_hls(scr); hl = hls[ci] if ci < len(hls) else (hls[0] if hls else "")
    chip_sentence(cv, W / 2, box[1] + 480, text, hl, 1330, 40, P.BG, P.INK, P.MARK, h=96)
    return cv.done()

# ---------- 복습 블록 ----------
def block(cv, box, idx, em, en, ko, text, hl, emph):
    x0, y0, x1, y1 = box; cx = (x0 + x1) / 2
    if emph:
        cv.shadow(box, 48, blur=22, alpha=90, dy=12)
        cv.rr(box, 48, fill=P.INK); ink, kc, chipf, chipi = P.WHITE, P.MARK, P.BG, P.INK
    else:
        cv.rr(box, 48, fill=P.WHITE, outline=P.LAV, width=4); ink, kc, chipf, chipi = P.INK_SOFT, P.INK_SOFT, mix(P.BG, P.WHITE, .4), P.INK_SOFT
    bs = 56
    cv.d.ellipse(((x0 + 34) * S, (y0 + 34) * S, (x0 + 34 + bs) * S, (y0 + 34 + bs) * S), fill=P.MARK if emph else P.LAV)
    cv.text((x0 + 34 + bs / 2, y0 + 34 + bs / 2 + 1), str(idx), font(INTER, 30), P.INK if emph else P.WHITE, "mm")
    cv.emo(em, 150, (cx - 75, y0 + 40), alpha=1.0 if emph else 0.55)
    fe, _ = fit_font(cv, INTER, en, 70, (x1 - x0) - 90)
    cv.text((cx, y0 + 285), en, fe, ink, "mm")
    cv.text((cx, y0 + 365), ko, font(KRB, 46), kc, "mm")
    chip_sentence(cv, cx, y0 + 450, text, hl, (x1 - x0) - 70, 34, chipf, chipi, P.MARK if emph else mix(P.MARK, P.WHITE, .5), h=88)

def note_block(cv, box, note, emph):
    x0, y0, x1, y1 = box; cx = (x0 + x1) / 2
    if emph: cv.shadow(box, 48, blur=22, alpha=90, dy=12); cv.rr(box, 48, fill=P.MARK); ink = P.INK
    else: cv.rr(box, 48, fill=mix(P.MARK, P.WHITE, .55), outline=P.LAV, width=4); ink = P.INK_SOFT
    f = font(KRB, 66)
    for i, l in enumerate(note["main"].split("\n")):
        cv.mixed(cx, y0 + 150 + i * 110, l, f, ink, 66)
    cv.text((cx, y0 + 450), note["sub"], font(KRB, 40), ink, "mm")

def recap_frame(cfg, pair, phase, N, photodir):
    cv = Cv(BG)
    header(cv, N, N, NS, NS, None, None, label=f"오늘의 표현 다시 보기 · {min(pair[0] + 1, N)}-{min(pair[1] + 1, N)}/{N}" if pair[1] != "note" else f"오늘의 표현 다시 보기 · {N}/{N}")
    boxes = [(80, 340, 930, 990), (990, 340, 1840, 990)]
    scr_by_card = {c: (s, i) for s in cfg["screens"] for i, c in enumerate(scr_cards(s))}
    for bi, item in enumerate(pair):
        emph = (bi == phase)
        if item == "note": note_block(cv, boxes[bi], cfg["note"], emph); continue
        em, en, ko = exprs.EXPRS[item]; s, ci = scr_by_card[en]; hls = scr_hls(s)
        chips = as_list(s.get("chips")); chip = chips[ci] if ci < len(chips) else " ".join(s["lines"])
        block(cv, boxes[bi], item + 1, em, en, ko, chip, hls[ci] if ci < len(hls) else (hls[0] if hls else ""), emph)
    return cv.done()

# ---------- 타임라인 ----------
def build_timeline(cfg, ep):
    sents = timing.SENTENCES
    tm = cfg.get("timing", {}); card_sec = tm.get("card", CARD_SEC); step_sec = tm.get("step", STEP_SEC)
    last_a = tm.get("last_a", LAST_A); last_b = tm.get("last_b", LAST_B)
    scr = cfg["screens"]; N = len(exprs.EXPRS)
    times = []
    for s in scr:
        ch = sents[s["sid"] - 1]["chunks"]
        times.append((ch[s["chunks"][0]][0], ch[s["chunks"][-1]][1]))
    vdur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", _os.path.join(ep, "voice.mp3")]))
    cuts = []
    for i, (a, b) in enumerate(times):
        st = max(0.0, a - 0.10); en = min(vdur, b + 0.30)
        if i > 0:
            pb = times[i - 1][1]
            if a - pb < 0.44:
                m = (a + pb) / 2; st = m
        if i + 1 < len(times):
            na = times[i + 1][0]
            if na - b < 0.44: en = (na + b) / 2
        cuts.append((st, en))
    items = []; collected = 0
    for i, s in enumerate(scr):
        st, en = cuts[i]; pad = max(0.0, 0.35 - (vdur - times[i][1])) if i == len(scr) - 1 else 0.0
        frames = int(round((en - st + pad) * FPS))
        items.append(dict(kind="screen", i=i, frames=frames, cut=(st, en), collected=collected, sid=s["sid"]))
        for ci, cname in enumerate(scr_cards(s)):
            k = [e[1] for e in exprs.EXPRS].index(cname); collected += 1
            items.append(dict(kind="card", i=i, ci=ci, k=k, frames=int(round(card_sec * FPS)), sid=s["sid"]))
    pairs = [(a, a + 1) for a in range(0, N - (N % 2), 2)] + ([(N - 1, "note")] if N % 2 else [])
    for pi, pr in enumerate(pairs):
        last = pi == len(pairs) - 1
        for ph in (0, 1):
            sec = (last_a if ph == 0 else last_b) if last else step_sec / 2
            items.append(dict(kind="recap", pair=pr, phase=ph, frames=int(round(sec * FPS)), sid=6))
    return items, times, cuts, vdur

def render_frames(cfg, ep, out):
    photodir = _os.path.join(ep, "photos"); N = len(exprs.EXPRS)
    items, *_ = build_timeline(cfg, ep)
    for n, it in enumerate(items):
        if it["kind"] == "screen":
            s = cfg["screens"][it["i"]]; pk = tuple(s["pkey"]) if len(s["pkey"]) > 1 else s["pkey"][0]
            cv = Cv(BG); header(cv, it["collected"], N, s["sid"] - 1, NS, photodir, pk); draw_sentence(cv, s); im = cv.done()
        elif it["kind"] == "card":
            im = card_frame(cfg, it["k"], N, cfg["screens"][it["i"]], photodir, it["ci"])
        else:
            im = recap_frame(cfg, it["pair"], it["phase"], N, photodir)
        it["png"] = _os.path.join(out, f"f{n:02d}_{it['kind']}.png"); im.save(it["png"])
    return items

def contact_sheet(items, out):
    th = [Image.open(i["png"]).resize((480, 270), Image.LANCZOS) for i in items]
    cols = 4; rows = math.ceil(len(th) / cols)
    sh = Image.new("RGB", (cols * 490, rows * 296), (30, 30, 30)); d = ImageDraw.Draw(sh)
    for k, (im, it) in enumerate(zip(th, items)):
        x, y = (k % cols) * 490, (k // cols) * 296
        sh.paste(im, (x, y + 22)); d.text((x + 4, y + 4), f"{k} {it['kind']} {it['frames'] / FPS:.2f}s", fill=(255, 255, 255))
    sh.save(out, quality=85)

# ---------- 오디오 ----------
SR = 44100
def pop_wave():
    L = int(0.18 * SR); tt = np.arange(L) / SR
    f = 500 + 1400 * tt / 0.18
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 22) + 0.3 * np.sin(2 * np.pi * 2600 * tt) * np.exp(-tt * 40)

def db(x): return 20 * math.log10(max(x, 1e-9))

def build_audio(cfg, ep, items, out_wav):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", _os.path.join(ep, "voice.mp3"), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    v = np.frombuffer(raw, np.float32)
    segs, pops, t = [], [], 0.0; report = []
    speech_rms = np.sqrt(np.mean(v[int(.2 * SR):int(2.3 * SR)] ** 2))
    for it in items:
        n = it["frames"] * SR // FPS
        if it["kind"] == "screen":
            a, b = [int(x * SR) for x in it["cut"]]; seg = v[a:b].copy()
            fi, fo = int(.015 * SR), int(.040 * SR)
            seg[:fi] *= np.linspace(0, 1, fi); seg[-fo:] *= np.linspace(1, 0, fo)
            seg = seg[:n] if len(seg) >= n else np.concatenate([seg, np.zeros(n - len(seg), np.float32)])
            tail = v[max(0, b - int(.04 * SR)):b]; head = v[a:a + int(.04 * SR)]
            report.append((it["i"], it["cut"], db(np.sqrt(np.mean(head ** 2))), db(np.sqrt(np.mean(tail ** 2)))))
        else:
            seg = np.zeros(n, np.float32); pops.append((t + 0.1, 1.0 if it["kind"] == "card" else 0.6))
        segs.append(seg); t += it["frames"] / FPS
    out = np.concatenate(segs).astype(np.float64)
    pw = pop_wave()
    sfx = np.zeros_like(out)
    for tp, g in pops:
        i = int(tp * SR); sfx[i:i + len(pw)] += pw[:max(0, min(len(pw), len(out) - i))] * g
    sfx = sfx / (np.abs(sfx).max() + 1e-9) * 0.8
    out = out + sfx * 0.35 * (np.abs(out).max() / 1.0)
    def wr(path, a):
        with wave.open(path, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.stack([a, a], 1) * 32767).astype(np.int16).tobytes())
    pre = out_wav + ".pre.wav"; wr(pre, np.clip(out / (np.abs(out).max() + 1e-9) * 0.8, -1, 1))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", pre, "-af", f"volume={-14 - I:.2f}dB,alimiter=limit=0.84:level=false", out_wav], check=True)
    _os.remove(pre)
    return report, db(speech_rms), t


# ---------- 썸네일 (1280x720) ----------
def thumb(cfg, ep, name, lines, hl_idx, pkey, zoom, chips, foot, maxsz=150):
    TW, TH = 1280, 720
    im = Image.new("RGBA", (TW * S, TH * S), P.BG + (255,))
    glow = Image.new("L", (TW * S, TH * S), 0); ImageDraw.Draw(glow).ellipse((-200 * S, 100 * S, 900 * S, 900 * S), fill=255)
    im.paste(Image.new("RGB", im.size, P.SUN), (0, 0), glow.filter(ImageFilter.GaussianBlur(120 * S)).point(lambda v: int(v * .6)))
    d = ImageDraw.Draw(im)
    # 사진 (오른쪽)
    px0, pw = 760, 520
    f, fx, fy = episode_cfg.PHOTOS[pkey]
    ph = Image.open(_os.path.join(ep, "photos", f)).convert("RGB")
    sc = max(pw * S / ph.width, TH * S / ph.height) * zoom
    ph = ph.resize((int(ph.width * sc + .5), int(ph.height * sc + .5)), Image.LANCZOS)
    x = min(max(fx * ph.width - pw * S / 2, 0), ph.width - pw * S); y = min(max(fy * ph.height - TH * S / 2, 0), ph.height - TH * S)
    ph = ph.crop((int(x), int(y), int(x) + pw * S, int(y) + TH * S)).convert("RGBA")
    im.alpha_composite(ph, (px0 * S, 0))
    # 제목
    fh = ImageFont.truetype(HAND, 60 * S); d.text((56 * S, 40 * S), "My English Diary", font=fh, fill=P.INK)
    y0 = 140 if chips else 190
    for i, line in enumerate(lines):
        sz = maxsz
        while sz > 70 and ImageFont.truetype(KRB, sz * S, index=1).getlength(line) / S > 660: sz -= 4
        ft = ImageFont.truetype(KRB, sz * S, index=1); w = ft.getlength(line) / S
        if i == hl_idx: d.rounded_rectangle((44 * S, (y0 + sz * .16) * S, (56 + w + 14) * S, (y0 + sz * 1.12) * S), 18 * S, fill=P.MARK)
        d.text((56 * S, y0 * S), line, font=ft, fill=P.INK); y0 += int(sz * 1.2)
    # 칩
    cy = y0 + 14
    fc = ImageFont.truetype(INTER, 36 * S)
    for c in chips:
        w = fc.getlength(c) / S + 56
        d.rounded_rectangle((56 * S, cy * S, (56 + w) * S, (cy + 62) * S), 31 * S, fill=P.INK)
        d.text(((56 + w / 2) * S, (cy + 31) * S), c, font=fc, fill=P.WHITE, anchor="mm"); cy += 74
    if foot:
        ff = ImageFont.truetype(KRB, 36 * S, index=1); d.text((56 * S, (TH - 70) * S), foot, font=ff, fill=P.INK_SOFT)
    out = _os.path.join(ep, "youtube", name)
    im.resize((TW, TH), Image.LANCZOS).convert("RGB").save(out, quality=92)
    return out

def make_thumbs(cfg, ep):
    out = []
    for t in cfg["thumbs"]:
        pk = t["pkey"]; pk = tuple(pk) if isinstance(pk, list) and len(pk) > 1 else (pk[0] if isinstance(pk, list) else pk)
        out.append(thumb(cfg, ep, t["name"], t["lines"], t["hl_idx"], pk, t.get("zoom", 1.0), t.get("chips", []), t.get("foot", ""), t.get("maxsz", 150)))
    return out

def fmt(t): return f"{int(t // 60)}:{int(t % 60):02d}"

def make_meta(cfg, ep, items):
    m = cfg["meta"]; t = 0.0; starts = {}
    for it in items:
        if it["kind"] == "screen": starts.setdefault(it["sid"], t)
        if it["kind"] == "recap": starts.setdefault("recap", t)
        t += it["frames"] / FPS
    total = t
    ch = [(starts[c["at"]] if c["at"] != 0 else 0.0, c["title"]) for c in m["chapters"]]
    ch_lines = "\n".join(f"{fmt(a)} {b}" for a, b in ch)
    assert len(ch) >= 3, "챕터는 3개 이상"
    for (a, _), (b, _) in zip(ch, ch[1:] + [(total, "")]): assert b - a >= 10, "챕터는 10초 이상"
    em = {int(k): v for k, v in m["alt_emoji"].items()}
    alt = []
    for s in timing.SENTENCES:
        en = " ".join(c[2] for c in s["chunks"]); ko = s["ko"].replace("\n", " ")
        alt.append(f"{en}\n{em[s['id']]} {ko}")
    expr = "\n".join(f"{e} {en}: {ko}" for e, en, ko in exprs.EXPRS)
    md = f"# 유튜브 메타 — {cfg['name']}\n\n## 제목 후보\n" + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(m["titles"])) + f"""

## 설명란 (복사해서 사용)
{m["intro"]}
지나쌤의 진짜 영어일기, 오늘의 표현 {len(exprs.EXPRS)}개와 함께 읽어요.

⏱ 챕터
{ch_lines}

📝 오늘의 표현
{expr}

📖 영어 일기 (한 줄씩 해석)
""" + "\n".join(alt) + """

✍️ 노트에 직접 써 보면 훨씬 도움돼요. 오늘 표현으로 한 줄씩 써 보세요!

#지나쌤영어 #realvibejina #영어공부하자 #영어일기 #영어표현
"""
    open(_os.path.join(ep, "youtube", "youtube_meta.md"), "w", encoding="utf-8").write(md)
    return total, ch

def main():
    ep = _os.path.abspath(sys.argv[1]); mode = sys.argv[2] if len(sys.argv) > 2 else "all"
    cfg = json.load(open(_os.path.join(ep, "youtube.json"), encoding="utf-8"))
    out = _os.path.join(ep, "youtube"); _os.makedirs(out, exist_ok=True)
    items = render_frames(cfg, ep, out) if mode in ("frames", "video", "all") else build_timeline(cfg, ep)[0]
    tot = sum(i["frames"] for i in items) / FPS
    print(f"화면 {len(items)}개, 총 {tot:.1f}s ({int(tot // 60)}:{tot % 60:04.1f})")
    if mode in ("frames", "all"): contact_sheet(items, _os.path.join(out, "sheet.jpg"))
    if mode in ("thumbs", "all"):
        for p in make_thumbs(cfg, ep): print("저장:", p)
    if mode in ("meta", "all"):
        total, ch = make_meta(cfg, ep, items); print("메타 저장, 챕터:", [(fmt(a), b) for a, b in ch])
    if mode in ("audio", "video", "all"):
        rep, sp, t = build_audio(cfg, ep, items, _os.path.join(out, "audio.wav"))
        print(f"음성 평균 {sp:.1f} dBFS 기준, 컷 지점 에너지(40ms RMS dBFS):")
        for i, c, h, tl in rep: print(f"  화면{i}: {c[0]:.2f}~{c[1]:.2f}s  시작 {h:.1f} / 끝 {tl:.1f}")
    if mode in ("video", "all"):
        lst = _os.path.join(out, "list.txt")
        with open(lst, "w") as f:
            for it in items: f.write(f"file '{it['png']}'\nduration {it['frames'] / FPS:.5f}\n")
            f.write(f"file '{items[-1]['png']}'\n")
        mp4 = _os.path.join(out, f"지나쌤_영어일기_{cfg['name']}_유튜브용.mp4")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", _os.path.join(out, "audio.wav"),
                        "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", mp4], check=True)
        print("저장:", mp4)

if __name__ == "__main__":
    main()
