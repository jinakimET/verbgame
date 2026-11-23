"""표지 전용 모듈 — 사진만 있으면 단독 실행됩니다 (render/음성 파일 불필요).

사용:
  python3 covers.py <에피소드폴더>/cover.json
cover.json 예:
{
  "photo": "cover.jpg", "fx": 0.5, "fy": 0.38,
  "keyword": "‘결국 이게 문제야’",
  "eng": [["It all comes"], [210, "to this."]],
  "block": [217, 131, 39], "ink": [236, 232, 175],
  "out": "표지_주제.png", "bright": 0.7, "vig": [0.4, 0.55, 0.65], "ksize": 120,
  "zoom": 1.0
}
zoom>1 이면 사진을 확대해 fx, fy 로 피사체를 글자 위쪽으로 올릴 수 있음.
경로는 json 이 있는 폴더 기준. eng 의 숫자 = 빈칸 밑줄 폭.
"""
import os as _os, sys, re, json
_HERE = _os.path.dirname(_os.path.abspath(__file__))
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

W, H = 1080, 1920
FD = _HERE + "/fonts/"
NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc"
EMOJI_TTF = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
WHITE = (255, 255, 255)

def F(n, s): return ImageFont.truetype(FD + n, s)
def krb(s): return ImageFont.truetype(NOTO % "Bold", s, index=1)   # Black 이 없으면 Bold
def kr(s): return ImageFont.truetype(NOTO % "Regular", s, index=1)
def tw(f, s): return f.getlength(s)

# ---- 이모지 섞어 그리기 (render2 의 것과 동일) ----
EMO_RE = re.compile(r"([☀-➿\U0001F000-\U0001FAFF]️?)")
_EF = None; _ecache = {}
def emoji(ch, size):
    global _EF
    if _EF is None: _EF = ImageFont.truetype(EMOJI_TTF, 109)
    k = (ch, size)
    if k in _ecache: return _ecache[k]
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=_EF, embedded_color=True)
    im = im.crop(im.getbbox())
    s = size / max(im.size)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    _ecache[k] = im
    return im

def draw_mixed(img, xy, text, font, fill, esize=None, measure=False):
    esize = esize or int(font.size * 1.05)
    x, y = xy; asc, _ = font.getmetrics()
    d = None if measure else ImageDraw.Draw(img)
    for p in [p for p in EMO_RE.split(text) if p]:
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

def photo(path, fx, fy, bright, zoom=1.0):
    im = Image.open(path).convert("RGB")
    s = max(W / im.width, H / im.height) * zoom
    im = im.resize((int(im.width * s + .5), int(im.height * s + .5)), Image.LANCZOS)
    x = min(max(fx * im.width - W / 2, 0), im.width - W); y = min(max(fy * im.height - H / 2, 0), im.height - H)
    im = im.crop((int(x), int(y), int(x) + W, int(y) + H))
    return ImageEnhance.Brightness(im).enhance(bright).convert("RGBA")

def vignette(img, top, mid, bottom):
    ys = np.arange(H)[:, None] / H
    a = np.clip((0.22 - ys) / 0.22, 0, 1) * top + np.exp(-((ys - 0.62) / 0.16) ** 2) * mid + np.clip((ys - 0.75) / 0.25, 0, 1) * bottom
    a = np.broadcast_to(a * 255, (H, W)).astype(np.uint8)
    img.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [Image.fromarray(a)]))

def stext(img, xy, text, font, fill, blur=10, alpha=150):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 4), text, font=font, fill=(0, 0, 0, alpha))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text(xy, text, font=font, fill=fill)

def cover(src, fx, fy, keyword, eng, block, ink, out, bright=0.82, vig=(0.35, 0.35, 0.6), ksize=150, zoom=1.0):
    img = photo(src, fx, fy, bright, zoom); vignette(img, *vig)
    d = ImageDraw.Draw(img)
    f = F("InstrumentSerif-Italic.ttf", 64); t = "My English Diary"
    stext(img, ((W - tw(f, t)) / 2, 270), t, f, WHITE)
    fk = krb(ksize); kw = tw(fk, keyword); kx = (W - kw) / 2; ky = 905
    asc, desc = fk.getmetrics()
    if kx < 40: print(f"[경고] 키워드가 화면 폭을 넘습니다 ({kw:.0f}px) — ksize 를 줄이세요")
    d.rectangle((kx - 22, ky + ksize * 0.2, kx + kw + 22, ky + asc + desc - ksize * 0.12), fill=block)
    d.text((kx, ky), keyword, font=fk, fill=WHITE)
    y = 1130
    for li, segs in enumerate(eng):
        fnt = F("InstrumentSerif-Regular.ttf" if li == 0 else "InstrumentSerif-Italic.ttf", 124)
        total = sum(s if isinstance(s, int) else tw(fnt, s) for s in segs) + 22 * sum(isinstance(s, int) for s in segs)
        if total > W - 80: print(f"[경고] 영어 {li+1}줄이 화면 폭을 넘습니다 ({total:.0f}px) — 줄을 나누세요")
        x = (W - total) / 2; a2, _ = fnt.getmetrics()
        for s in segs:
            if isinstance(s, int):
                d.rounded_rectangle((x, y + a2 - 8, x + s, y + a2 + 2), radius=5, fill=ink); x += s + 22
            else:
                stext(img, (x, y), s, fnt, ink); x += tw(fnt, s)
        y += 132
    fs = kr(42); s = "오늘의 에피소드, 마지막 표현까지 놓치지 마요 👀"
    draw_mixed(img, ((W - mixed_w(s, fs, 46)) / 2, y + 70), s, fs, WHITE, 46)
    fe = F("InstrumentSerif-Italic.ttf", 52); e = "Today’s episode — don’t miss the last expression"
    stext(img, ((W - tw(fe, e)) / 2, y + 135), e, fe, ink, blur=6, alpha=130)
    img.convert("RGB").save(out)

def from_json(path):
    base = _os.path.dirname(_os.path.abspath(path)); c = json.load(open(path, encoding="utf-8"))
    p = lambda n: _os.path.join(base, n)
    out = p(c["out"])
    cover(p(c["photo"]), c.get("fx", .5), c.get("fy", .4), c["keyword"], c["eng"],
          tuple(c["block"]), tuple(c["ink"]), out, c.get("bright", .75),
          tuple(c.get("vig", (.35, .45, .6))), c.get("ksize", 120), c.get("zoom", 1.0))
    Image.open(out).resize((540, 960)).save(p("cover_prev.jpg"), quality=88)
    print("저장:", out, "+ cover_prev.jpg")

if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    from_json(sys.argv[1])
