#!/usr/bin/env python3
"""타이핑 교정 릴스 렌더러 (어법 / 어휘 공용).

사용:
  python3 reels/render/render_reel.py reels/sets/grammar-002/episodes.json          # 세트 전체
  python3 reels/render/render_reel.py reels/sets/grammar-002/episodes.json --only 3 # 3번 편만
  python3 reels/render/render_reel.py --cover decide "안 틀리게 쓰는 법" -o cover.png  # 표지

episodes.json 형식은 reels/SPEC.md 의 '에피소드 JSON' 절 참고.
출력: 같은 폴더의 out/ 아래 mp4 + 검수용 프레임 PNG(pen / chip / contact sheet).
"""
import argparse, json, math, os, re, struct, subprocess, sys, wave, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # reels/
FONT_DIR = os.path.join(ROOT, "fonts")
ASSET_DIR = os.path.join(ROOT, "assets")
LEVELS = ["중하", "중상", "고하", "고상", "어학"]
BG = (10, 10, 12)
RED = (255, 59, 48)
PEN_COLORS = {"빨강": (255, 59, 48), "노랑": (255, 214, 10), "주황": (255, 149, 0),
              "초록": (60, 220, 100), "파랑": (64, 160, 255)}
ACCENT_COLORS = {"코랄": (255, 136, 130), "민트": (72, 240, 190)}
HANDLE = "@jina.ssam_english"

# ---------------------------------------------------------------- fonts
def _find(patterns, fallback):
    for p in patterns:
        hits = sorted(glob.glob(os.path.join(FONT_DIR, p)))
        if hits:
            return hits[0]
    for f in fallback:
        if os.path.exists(f):
            return f
    raise SystemExit(f"폰트를 찾을 수 없습니다: {patterns}\n→ reels/fonts/ 에 폰트를 넣거나 `apt-get install -y fonts-nanum` 을 실행하세요.")

NANUM = "/usr/share/fonts/truetype/nanum/"
FONT_PATHS = {
    "en": _find(["Paperlogy*7*.ttf", "Paperlogy*Bold*.ttf", "Paperlogy*.ttf"],
                [NANUM + "NanumSquareB.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]),
    "ui": _find(["Paperlogy*6*.ttf", "Paperlogy*SemiBold*.ttf", "Paperlogy*.ttf"],
                [NANUM + "NanumSquareB.ttf"]),
    "ko": _find(["EF_jejudoldam*.ttf", "EF_Jejudoldam*.ttf", "*jejudoldam*.ttf", "*Doldam*.ttf"],
                [NANUM + "NanumSquareB.ttf"]),
    "hand": _find(["*Pen*.ttf", "*pen*.ttf", "*Hand*.ttf", "*hand*.ttf"],
                  ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]),
}
_fcache = {}
def F(kind, size):
    k = (kind, size)
    if k not in _fcache:
        _fcache[k] = ImageFont.truetype(FONT_PATHS[kind], size)
    return _fcache[k]

def tw(font, s):
    return font.getlength(s)

# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3

def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)

def parse_color(v, table, default):
    if v is None or v == "" or v == "그대로":
        return default
    if isinstance(v, (list, tuple)):
        return tuple(int(c) for c in v[:3])
    v = str(v).strip()
    if v in table:
        return table[v]
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", v)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"\(?\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)?", v)
    if m:
        return tuple(int(c) for c in m.groups())
    raise SystemExit(f"색을 이해하지 못했습니다: {v}")

def darken(c, k):
    return tuple(int(x * k) for x in c)

def mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))

TOKEN = re.compile(r"\{([^{}>]+)>([^{}]+)\}")

def parse_line(line):
    """'If I {know>knew} his' -> segments [(text, kind, right)] kind: plain|wrong"""
    segs, pos = [], 0
    for m in TOKEN.finditer(line):
        if m.start() > pos:
            segs.append((line[pos:m.start()], "plain", None))
        segs.append((m.group(1), "wrong", m.group(2)))
        pos = m.end()
    if pos < len(line):
        segs.append((line[pos:], "plain", None))
    return segs

def corrected_segments(line):
    out, pos = [], 0
    for m in TOKEN.finditer(line):
        if m.start() > pos:
            out.append((line[pos:m.start()], False))
        out.append((m.group(2), True))
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], False))
    return out

def split_ko_hint(ko):
    """'나는 [[두꺼운]] 책을' -> [(text, is_hint)]"""
    parts = re.split(r"(\[\[[^\]]+\]\])", ko)
    return [(p[2:-2], True) if p.startswith("[[") else (p, False) for p in parts if p]

# ---------------------------------------------------------------- audio
SR = 44100

def synth_audio(events, total, path):
    n = int(total * SR) + SR
    buf = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(7)
    for kind, t in events:
        i = int(t * SR)
        if kind == "key":
            L = int(0.035 * SR)
            env = np.exp(-np.linspace(0, 9, L))
            noise = rng.standard_normal(L) * 0.5
            click = np.sin(2 * np.pi * rng.uniform(1800, 2600) * np.arange(L) / SR) * 0.35
            s = (noise + click) * env * 0.35
        elif kind == "scratch":
            L = int(0.28 * SR)
            env = np.sin(np.linspace(0, np.pi, L)) ** 0.6
            noise = rng.standard_normal(L)
            noise = np.convolve(noise, np.ones(6) / 6, mode="same")
            s = noise * env * 0.22
        elif kind == "write":
            L = int(0.6 * SR)
            env = np.sin(np.linspace(0, np.pi, L)) ** 0.8 * (0.6 + 0.4 * np.sin(np.linspace(0, 30, L)) ** 2)
            noise = np.convolve(rng.standard_normal(L), np.ones(10) / 10, mode="same")
            s = noise * env * 0.18
        elif kind == "pop":
            L = int(0.18 * SR)
            x = np.arange(L) / SR
            s = np.sin(2 * np.pi * (520 + 900 * x) * x) * np.exp(-x * 22) * 0.35
        elif kind == "ding":
            L = int(0.6 * SR)
            x = np.arange(L) / SR
            s = (np.sin(2 * np.pi * 1320 * x) + 0.5 * np.sin(2 * np.pi * 1980 * x)) * np.exp(-x * 7) * 0.18
        else:
            continue
        j = min(n, i + len(s))
        buf[i:j] += s[: j - i]
    buf = buf[: int(total * SR)]
    peak = float(np.max(np.abs(buf))) or 1.0
    if peak > 0.95:
        buf *= 0.95 / peak
    pcm = (buf * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

# ---------------------------------------------------------------- drawing pieces
def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def draw_pills(img, level, combo):
    d = ImageDraw.Draw(img)
    f = F("ui", 34)
    pw, ph, gap = 150, 62, 16
    x0 = (W - (5 * pw + 4 * gap)) // 2
    y0 = 270
    for i, name in enumerate(LEVELS):
        x = x0 + i * (pw + gap)
        on = (i + 1) == level
        if on:
            rrect(d, (x, y0, x + pw, y0 + ph), ph // 2, fill=(245, 245, 247))
            col = (12, 12, 14)
        else:
            rrect(d, (x, y0, x + pw, y0 + ph), ph // 2, outline=(70, 70, 76), width=3)
            col = (95, 95, 102)
        d.text((x + pw / 2, y0 + ph / 2 + 1), name, font=f, fill=col, anchor="mm")
    if combo:
        f2 = F("ui", 30)
        label = "종합편"
        w = tw(f2, label) + 44
        x = (W - w) / 2
        rrect(d, (x, y0 + ph + 22, x + w, y0 + ph + 22 + 52), 26, fill=RED)
        d.text((W / 2, y0 + ph + 22 + 27), label, font=f2, fill=(255, 255, 255), anchor="mm")

def draw_pen(img, tip, color, angle_deg=35, alpha=1.0):
    """tip=(x,y) 펜 끝. 몸통은 오른쪽 아래로 뻗는다."""
    if alpha <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)          # 몸통 방향
    px, py = -uy, ux                           # 수직
    tx, ty = tip

    def pt(along, side):
        return (tx + ux * along + px * side, ty + uy * along + py * side)

    A = int(255 * alpha)
    # 금속 촉
    d.polygon([pt(0, 0), pt(34, -11), pt(34, 11)], fill=(200, 200, 206, A))
    d.polygon([pt(0, 0), pt(12, -4), pt(12, 4)], fill=color + (A,))
    # 그립
    d.polygon([pt(34, -13), pt(80, -15), pt(80, 15), pt(34, 13)], fill=(40, 40, 44, A))
    # 몸통
    d.polygon([pt(80, -16), pt(300, -16), pt(300, 16), pt(80, 16)], fill=color + (A,))
    d.polygon([pt(80, -16), pt(300, -16), pt(300, -7), pt(80, -7)], fill=(255, 255, 255, int(A * 0.25)))
    # 클립 + 꼬리
    d.polygon([pt(230, -16), pt(290, -16), pt(290, -24), pt(236, -24)], fill=(210, 210, 216, A))
    d.polygon([pt(300, -16), pt(318, -12), pt(318, 12), pt(300, 16)], fill=darken(color, 0.7) + (A,))
    img.alpha_composite(layer)

def lerp_path(points, k):
    """points 리스트를 따라 0..1 진행. 그려진 부분 좌표 목록과 끝점 반환."""
    if k <= 0:
        return [points[0]], points[0]
    segs = [math.dist(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(segs) or 1
    goal = total * clamp(k)
    out, acc = [points[0]], 0
    for i, L in enumerate(segs):
        if acc + L >= goal:
            r = (goal - acc) / L if L else 1
            p = (points[i][0] + (points[i + 1][0] - points[i][0]) * r,
                 points[i][1] + (points[i + 1][1] - points[i][1]) * r)
            out.append(p)
            return out, p
        acc += L
        out.append(points[i + 1])
    return out, points[-1]

def draw_save_badge(d, x, y, h=64):
    f = F("ui", 32)
    w = 150
    rrect(d, (x, y, x + w, y + h), h // 2, fill=(250, 250, 252))
    bx, by = x + 30, y + 15
    d.polygon([(bx, by), (bx + 26, by), (bx + 26, by + 34), (bx + 13, by + 24), (bx, by + 34)], fill=RED)
    d.text((x + 100, y + h / 2 + 1), "저장", font=f, fill=(20, 20, 24), anchor="mm")
    return w

# ---------------------------------------------------------------- episode layout
class Episode:
    def __init__(self, ep, cfg, mode):
        self.ep, self.mode = ep, mode
        self.level = int(ep["level"])
        self.combo = bool(ep.get("combo", self.level >= 4 and mode == "grammar" and ep.get("combo") is not False and len(ep.get("points", [])) > 1))
        self.pen = parse_color(cfg.get("pen"), PEN_COLORS, PEN_COLORS["빨강"])
        self.acc = parse_color(cfg.get("accent"), ACCENT_COLORS, ACCENT_COLORS["코랄"])
        self.lines = ep["lines"]
        self.fen = F("en", 66)
        self.lh = 144 if mode == "words" else 150
        self.problems = []
        self._layout()
        self._timeline()

    # -- typing layout
    def _layout(self):
        n = len(self.lines)
        block_h = n * self.lh
        self.top = 620 if self.mode == "words" else int(860 - block_h / 2)
        self.x0 = 130
        self.chars = []        # (x, y, ch, color, line_idx)
        self.wrongs = []       # dict(bbox, right, line)
        for li, line in enumerate(self.lines):
            y = self.top + li * self.lh
            x = self.x0
            width = sum(tw(self.fen, s) for s, _, _ in parse_line(line))
            if width > 830:
                self.problems.append(f"{li+1}번째 줄 폭 {int(width)}px > 830px: '{TOKEN.sub(lambda m: m.group(1), line)}'")
            for text, kind, right in parse_line(line):
                col = self.pen if kind == "wrong" else (245, 245, 247)
                x_start = x
                for ch in text:
                    self.chars.append((x, y, ch, col, li))
                    x += tw(self.fen, ch)
                if kind == "wrong":
                    asc, desc = self.fen.getmetrics()
                    bb = (x_start - 6, y + 8, x + 6, y + asc + 4)
                    self.wrongs.append({"bbox": bb, "right": right, "line": li})
        if not self.wrongs:
            raise SystemExit("오류 표시가 없습니다. lines 안에 {오답>정답} 을 넣어 주세요.")
        # 손글씨 정답 위치
        fh = F("hand", 76)
        for w in self.wrongs:
            x1, y1, x2, y2 = w["bbox"]
            cw = tw(fh, w["right"])
            cx = (x1 + x2) / 2
            left = cx - cw / 2
            left = max(60, left)
            if left + cw > W - 60:
                self.problems.append(f"손글씨 정답 '{w['right']}' 가 오른쪽으로 넘칩니다 (끝 {int(left+cw)}px)")
                left = W - 60 - cw
            w["hand_xy"] = (left, y1 - 74)
            w["hand_w"] = cw
        # 어휘: 한글 문장 위치
        if self.mode == "words":
            self.fko = F("ko", 54)
            self.ko_parts = split_ko_hint(self.ep["ko"])
            ko_w = sum(tw(self.fko, p) for p, _ in self.ko_parts)
            if ko_w > 900:
                self.problems.append(f"한글 문장 폭 {int(ko_w)}px > 900px")
            self.ko_y = self.top + len(self.lines) * self.lh + 70
            self.ko_x = (W - ko_w) / 2
            x = self.ko_x
            self.hint_box = None
            for p, hint in self.ko_parts:
                pw = tw(self.fko, p)
                if hint:
                    self.hint_box = (x, self.ko_y, x + pw, self.ko_y + 60)
                x += pw
            if self.hint_box is None:
                raise SystemExit("어휘 편 ko 에는 [[힌트 단어]] 표시가 필요합니다.")
            w0 = self.wrongs[0]
            hx1, hy1, hx2, hy2 = self.hint_box
            wx1, wy1, wx2, wy2 = w0["bbox"]
            # 한글 힌트 위 → 영어와 한글 사이 빈 줄 → 왼쪽 여백 쪽으로 돌아 → 오답 단어 아래
            last_bottom = self.top + (len(self.lines) - 1) * self.lh + 86
            gap_y = (last_bottom + self.ko_y - 22) / 2
            hcx, wcx = (hx1 + hx2) / 2, (wx1 + wx2) / 2
            gutter = 72
            pts = [(hcx, self.ko_y - 30), (hcx, gap_y), (gutter, gap_y)]
            if w0["line"] == len(self.lines) - 1:
                pts += [(gutter, wy2 + 22), (wcx, wy2 + 22)]
            else:
                # 오답이 윗줄이면 왼쪽 여백을 따라 올라가 그 줄 아래 틈으로 들어간다
                under = wy2 + (self.lh - 86) / 2 + 4
                pts += [(gutter, under), (wcx, under)]
            pts.append((wcx, wy2 + 6))
            self.arrow_pts = pts

    # -- timeline
    def _timeline(self):
        t = 0.6
        self.t_type0 = t
        cps = 0.065
        self.char_t = []
        for i, c in enumerate(self.chars):
            self.char_t.append(t)
            t += cps * (2.2 if c[2] in ",." else 1.0)
            if i + 1 < len(self.chars) and self.chars[i + 1][4] != c[4]:
                t += 0.25
        self.t_type1 = t
        t += 0.5
        if self.mode == "words":
            self.t_ko = t; t += 0.5
            t += 0.5 * 1.4                       # 한글 뜬 뒤 여유(40%)
            self.t_arrow = t; t += 0.7
            t += 0.4
        self.t_pen_in = t; t += 0.45
        self.pen_steps = []
        for w in self.wrongs:
            x1, y1, x2, y2 = w["bbox"]
            s1 = t; t += 0.32
            s2 = t + 0.08; t = s2 + 0.32
            h0 = t + 0.18; t = h0 + 0.7
            self.pen_steps.append((w, s1, s2, h0))
            t += 0.25
        self.t_pen_out = t; t += 0.4
        t += 0.9
        self.t_swap = t; t += 0.35               # 타이핑 화면 → 박스
        self.t_box = t; t += 0.4
        t += 3.0 * 1.2                           # 박스 노출 20% 길게
        self.t_chip = t; t += 0.45
        t += 1.2
        self.t_handle = t; t += 0.4
        t += 1.0
        self.t_spot = t                           # 스포트라이트 0.12 페이드
        t += 0.12 + 1.6 + 0.12
        t += 0.8
        self.total = t
        # 박스/칩 레이아웃 미리 계산
        self._final_layout()

    def _final_layout(self):
        fb = F("en", 56)
        fk = F("ui", 38)
        pad = 48
        lines = [corrected_segments(l) for l in self.lines]
        widths = [sum(tw(fb, s) for s, _ in segs) for segs in lines]
        ko = self.ep.get("ko_box") or re.sub(r"\[\[|\]\]", "", self.ep["ko"])
        ko_lines = ko.split("\n")
        kw = max(tw(fk, k) for k in ko_lines)
        bw = int(min(960, max(max(widths), kw) + pad * 2))
        lh, klh = 82, 54
        bh = int(pad + len(lines) * lh + 18 + len(ko_lines) * klh + pad - 10)
        top = 560
        self.box = ((W - bw) / 2, top, (W + bw) / 2, top + bh)
        self.box_lines = lines
        self.box_ko = ko_lines
        self.fb, self.fk, self.box_pad, self.box_lh, self.box_klh = fb, fk, pad, lh, klh
        if max(widths) + pad * 2 > 960:
            self.problems.append("정답 박스 영어 줄이 박스 폭(960)을 넘습니다")
        # 칩
        chip = self.ep["chip"]
        ft, fs, fr = F("en", 46), F("ui", 34), F("ui", 34)
        cw = 900
        y = 0
        items = []
        items.append(("title", chip["title"], ft, 64))
        if chip.get("sub"):
            items.append(("sub", chip["sub"], fs, 52))
        rows = chip.get("rows", [])[:3]
        if self.level >= 3 and any(len(r) < 2 or not r[1] for r in rows):
            self.problems.append("고하·고상·어학 칩은 모든 행에 한글 뜻이 필요합니다")
        if rows:
            y_sep = True
        for r in rows:
            items.append(("row", r, fr, 54))
        ch = 40 + sum(h for *_, h in items) + (22 if rows else 0) + 30
        self.chip_items = items
        self.chip = ((W - cw) / 2, self.box[3] + 44, (W + cw) / 2, self.box[3] + 44 + ch)
        for kind, val, f, _ in items:
            txt = val if isinstance(val, str) else f"{val[0]}  |  {val[1] if len(val) > 1 else ''}"
            if tw(f, txt) > cw - 70:
                self.problems.append(f"칩 텍스트가 칩 폭을 넘습니다: {txt}")
        self.handle_y = self.chip[3] + 40
        if self.handle_y + 64 > 1680:
            self.problems.append(f"핸들/저장 배지가 안전영역(1680) 밖입니다: y={int(self.handle_y + 64)}")

    # -- rendering
    def frame(self, t):
        img = Image.new("RGBA", (W, H), BG + (255,))
        draw_pills(img, self.level, self.combo)
        if t < self.t_swap + 0.35:
            a = 1 - prog(t, self.t_swap, 0.35)
            self._typing_scene(img, t, a)
        if t >= self.t_box:
            self._final_scene(img, t)
        return img

    def _typing_scene(self, img, t, alpha):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        shown = sum(1 for ct in self.char_t if ct <= t)
        for i in range(shown):
            x, y, ch, col, li = self.chars[i]
            d.text((x, y), ch, font=self.fen, fill=col)
        # 커서
        typing = t < self.t_type1 + 0.4
        if typing or (t < self.t_pen_in):
            blink = (int(t * 2.4) % 2 == 0) or (self.t_type0 <= t <= self.t_type1)
            if blink and t >= 0.15:
                if shown:
                    x, y, ch, col, li = self.chars[shown - 1]
                    cx = x + tw(self.fen, ch) + 4
                    cy = y
                else:
                    cx, cy = self.x0, self.top
                d.rectangle((cx, cy + 6, cx + 5, cy + 74), fill=(245, 245, 247))
        # 어휘: 한글 문장 + 화살표
        if self.mode == "words" and t >= self.t_ko:
            k = ease(prog(t, self.t_ko, 0.5))
            yoff = (1 - k) * 30
            ka = int(255 * k)
            hx = self.ko_x
            bb = (self.ko_x - 34, self.ko_y - 22 + yoff, self.ko_x + sum(tw(self.fko, p) for p, _ in self.ko_parts) + 34, self.ko_y + 80 + yoff)
            self._dotted_rect(d, bb, (150, 150, 158, int(ka * 0.8)))
            for p, hint in self.ko_parts:
                d.text((hx, self.ko_y + yoff), p, font=self.fko, fill=(self.pen if hint else (240, 240, 242)) + (ka,))
                hx += tw(self.fko, p)
            if t >= self.t_arrow:
                pts, end = lerp_path(self.arrow_pts, ease(prog(t, self.t_arrow, 0.7)))
                if len(pts) > 1:
                    d.line(pts, fill=self.pen + (255,), width=4, joint="curve")
                if prog(t, self.t_arrow, 0.7) >= 1:
                    ex, ey = self.arrow_pts[-1]
                    d.polygon([(ex, ey), (ex - 13, ey + 22), (ex + 13, ey + 22)], fill=self.pen + (255,))
        # 펜 교정
        pen_tip, pen_a = None, 0.0
        fh = F("hand", 76)
        for w, s1, s2, h0 in self.pen_steps:
            x1, y1, x2, y2 = w["bbox"]
            p1 = [(x1, y1), (x2, y2)]
            p2 = [(x2, y1), (x1, y2)]
            for (pts, st) in ((p1, s1), (p2, s2)):
                if t >= st:
                    drawn, end = lerp_path(pts, ease(prog(t, st, 0.32)))
                    d.line(drawn, fill=self.pen + (255,), width=8)
                    if t < st + 0.32:
                        pen_tip = end
            if t >= h0:
                k = prog(t, h0, 0.7)
                hx, hy = w["hand_xy"]
                txt = Image.new("RGBA", (int(w["hand_w"]) + 30, 110), (0, 0, 0, 0))
                ImageDraw.Draw(txt).text((10, 0), w["right"], font=fh, fill=self.pen + (255,))
                txt = txt.rotate(4, resample=Image.BICUBIC, expand=False)
                reveal = int(txt.width * ease(k))
                if reveal > 0:
                    layer.alpha_composite(txt.crop((0, 0, reveal, txt.height)), (int(hx - 10), int(hy)))
                if k < 1:
                    pen_tip = (hx + reveal - 10, hy + 62 + 6 * math.sin(t * 40))
        # 펜 진입/퇴장
        if self.t_pen_in <= t < self.t_pen_out + 0.4:
            first = self.pen_steps[0]
            x1, y1, _, _ = first[0]["bbox"]
            rest = (x1, y1)
            if t < self.t_pen_in + 0.45:
                k = ease(prog(t, self.t_pen_in, 0.45))
                pen_tip = (rest[0] + (1 - k) * 500, rest[1] + (1 - k) * 600)
                pen_a = k
            elif t >= self.t_pen_out:
                k = ease(prog(t, self.t_pen_out, 0.4))
                last = self.pen_steps[-1][0]
                lx, ly = last["hand_xy"][0] + last["hand_w"], last["hand_xy"][1] + 62
                pen_tip = (lx + k * 500, ly + k * 600)
                pen_a = 1 - k
            else:
                pen_a = 1.0
                if pen_tip is None:
                    # 단계 사이: 다음 시작점으로 이동
                    pen_tip = self._pen_idle(t)
        img_t = layer
        if alpha < 1:
            a = np.array(img_t)
            a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
            img_t = Image.fromarray(a)
        img.alpha_composite(img_t)
        if pen_tip and pen_a > 0:
            draw_pen(img, pen_tip, self.pen, alpha=pen_a * alpha)

    def _pen_idle(self, t):
        prev = None
        for w, s1, s2, h0 in self.pen_steps:
            x1, y1, x2, y2 = w["bbox"]
            marks = [(s1, (x1, y1)), (s1 + 0.32, (x2, y2)), (s2, (x2, y1)), (s2 + 0.32, (x1, y2)),
                     (h0, (w["hand_xy"][0], w["hand_xy"][1] + 62)),
                     (h0 + 0.7, (w["hand_xy"][0] + w["hand_w"], w["hand_xy"][1] + 62))]
            for mt, mp in marks:
                if prev and prev[0] <= t < mt:
                    k = ease((t - prev[0]) / (mt - prev[0]))
                    return (prev[1][0] + (mp[0] - prev[1][0]) * k, prev[1][1] + (mp[1] - prev[1][1]) * k)
                prev = (mt, mp)
        return prev[1] if prev else (W / 2, H / 2)

    def _dotted_rect(self, d, bb, col):
        x1, y1, x2, y2 = bb
        step, dash = 14, 7
        for x in np.arange(x1, x2, step):
            d.line([(x, y1), (min(x + dash, x2), y1)], fill=col, width=2)
            d.line([(x, y2), (min(x + dash, x2), y2)], fill=col, width=2)
        for y in np.arange(y1, y2, step):
            d.line([(x1, y), (x1, min(y + dash, y2))], fill=col, width=2)
            d.line([(x2, y), (x2, min(y + dash, y2))], fill=col, width=2)

    def _final_scene(self, img, t):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        k = ease(prog(t, self.t_box, 0.4))
        x1, y1, x2, y2 = self.box
        rrect(d, (x1, y1, x2, y2), 30, fill=self.acc + (255,))
        pad, lh = self.box_pad, self.box_lh
        dark = (24, 18, 20)
        hl_bg = darken(self.acc, 0.18)
        for li, segs in enumerate(self.box_lines):
            # 하이라이트 바로 앞/뒤에 공백 없이 붙은 글자(쉼표 등)가 박스에 가려지지 않게 간격을 둔다
            gaps = []
            for i, (s, hl) in enumerate(segs):
                gl = gr = 0
                if hl:
                    if i > 0 and segs[i - 1][0] and not segs[i - 1][0][-1].isspace():
                        gl = 10
                    if i + 1 < len(segs) and segs[i + 1][0] and not segs[i + 1][0][0].isspace():
                        gr = 10
                gaps.append((gl, gr))
            lw = sum(tw(self.fb, s) + gl + gr for (s, _), (gl, gr) in zip(segs, gaps))
            x = (W - lw) / 2
            y = y1 + pad + li * lh
            for (s, hl), (gl, gr) in zip(segs, gaps):
                sw = tw(self.fb, s)
                x += gl
                if hl:
                    rrect(d, (x - 7, y - 2, x + sw + 7, y + 70), 14, fill=hl_bg + (255,))
                    d.text((x, y), s, font=self.fb, fill=self.acc + (255,))
                else:
                    d.text((x, y), s, font=self.fb, fill=dark + (255,))
                x += sw + gr
        ky = y1 + pad + len(self.box_lines) * lh + 18
        for kl in self.box_ko:
            d.text((W / 2, ky), kl, font=self.fk, fill=darken(dark, 1.0) + (255,), anchor="mt")
            ky += self.box_klh
        # 초록새 (있을 때만)
        bird = os.path.join(ASSET_DIR, "bird.png")
        if os.path.exists(bird):
            b = Image.open(bird).convert("RGBA")
            bh = 150
            b = b.resize((int(b.width * bh / b.height), bh), Image.LANCZOS)
            layer.alpha_composite(b, (int(x2 - b.width - 50), int(y1 - bh + 18)))
        # 칩
        if t >= self.t_chip:
            self._chip(d, t)
        # 핸들 + 저장
        if t >= self.t_handle:
            self._handle(d, t)
        # 박스 등장 스케일 효과
        if k < 1:
            sc = 0.92 + 0.08 * k
            cx, cy = W / 2, (y1 + y2) / 2
            lw_, lh_ = int(W * sc), int(H * sc)
            small = layer.resize((lw_, lh_), Image.BICUBIC)
            tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            tmp.alpha_composite(small, (int(cx - cx * sc), int(cy - cy * sc)))
            a = np.array(tmp); a[..., 3] = (a[..., 3] * k).astype(np.uint8)
            layer = Image.fromarray(a)
        img.alpha_composite(layer)
        # 스포트라이트
        sp_in, sp_hold = 0.12, 1.6
        if self.t_spot <= t < self.t_spot + sp_in * 2 + sp_hold:
            if t < self.t_spot + sp_in:
                s = prog(t, self.t_spot, sp_in)
            elif t < self.t_spot + sp_in + sp_hold:
                s = 1.0
            else:
                s = 1 - prog(t, self.t_spot + sp_in + sp_hold, sp_in)
            mask = Image.new("L", (W, H), int(170 * s))
            md = ImageDraw.Draw(mask)
            md.rounded_rectangle((x1 - 26, y1 - 26, x2 + 26, y2 + 26), radius=44, fill=0)
            mask = mask.filter(ImageFilter.GaussianBlur(22))
            shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            shade.putalpha(mask)
            img.alpha_composite(shade)

    def _chip(self, d, t):
        k = ease(prog(t, self.t_chip, 0.45))
        x1, y1, x2, y2 = self.chip
        off = (1 - k) * 24
        A = int(255 * k)
        rrect(d, (x1, y1 + off, x2, y2 + off), 26, fill=darken(self.acc, 0.2) + (A,), outline=self.acc + (A,), width=4)
        y = y1 + 40 + off
        first_row = True
        for kind, val, f, h in self.chip_items:
            if kind == "title":
                d.text((W / 2, y), val, font=f, fill=self.acc + (A,), anchor="mt")
            elif kind == "sub":
                d.text((W / 2, y), val, font=f, fill=(225, 225, 230, A), anchor="mt")
            else:
                if first_row:
                    d.line([(x1 + 50, y + 4), (x2 - 50, y + 4)], fill=self.acc + (int(A * 0.5),), width=2)
                    y += 22
                    first_row = False
                en, ko = val[0], (val[1] if len(val) > 1 else "")
                fe = F("en", 34)
                we, wk = tw(fe, en), tw(f, ko)
                sep = "  |  " if ko else ""
                ws = tw(f, sep)
                x = (W - (we + ws + wk)) / 2
                d.text((x, y), en, font=fe, fill=(250, 250, 252, A))
                d.text((x + we, y), sep, font=f, fill=self.acc + (A,))
                d.text((x + we + ws, y), ko, font=f, fill=(200, 200, 208, A))
            y += h

    def _handle(self, d, t):
        k = ease(prog(t, self.t_handle, 0.4))
        A = int(255 * k)
        f = F("ui", 40)
        hw = tw(f, HANDLE)
        total = hw + 24 + 150
        x = (W - total) / 2
        y = self.handle_y
        d.text((x, y + 32), HANDLE, font=f, fill=(240, 240, 244, A), anchor="lm")
        tmp = Image.new("RGBA", (160, 70), (0, 0, 0, 0))
        draw_save_badge(ImageDraw.Draw(tmp), 0, 0)
        if A < 255:
            a = np.array(tmp); a[..., 3] = (a[..., 3] * k).astype(np.uint8); tmp = Image.fromarray(a)
        d._image.alpha_composite(tmp, (int(x + hw + 24), int(y)))

    def audio_events(self):
        ev = [("key", ct) for ct, c in zip(self.char_t, self.chars) if c[2] != " "]
        if self.mode == "words":
            ev.append(("pop", self.t_ko))
        for w, s1, s2, h0 in self.pen_steps:
            ev += [("scratch", s1), ("scratch", s2), ("write", h0)]
        ev += [("pop", self.t_box), ("pop", self.t_chip), ("ding", self.t_spot)]
        return ev


# ---------------------------------------------------------------- output
def render_episode(ep, cfg, mode, out_dir, set_no, idx):
    e = Episode(ep, cfg, mode)
    prefix = "어법" if mode == "grammar" else "어휘"
    name = f"{prefix}{set_no}-{idx}_{LEVELS[e.level - 1]}"
    os.makedirs(out_dir, exist_ok=True)
    mp4 = os.path.join(out_dir, name + ".mp4")
    wav = os.path.join(out_dir, name + ".wav")
    synth_audio(e.audio_events(), e.total, wav)
    nframes = int(math.ceil(e.total * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-preset", "medium", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    checks = {
        "pen": (e.pen_steps[-1][3] + 0.6),
        "chip": e.t_spot - 0.2,
        "spot": e.t_spot + 0.6,
    }
    if mode == "words":
        checks["arrow"] = e.t_arrow + 0.75
    want = {int(v * FPS): k for k, v in checks.items()}
    sheet_times = [e.t_type1 - 0.1, checks["pen"], e.t_box + 1.0, checks["chip"]]
    sheet = {}
    for fi in range(nframes):
        t = fi / FPS
        fr = e.frame(t).convert("RGB")
        p.stdin.write(fr.tobytes())
        if fi in want:
            fr.save(os.path.join(out_dir, f"{name}__check_{want[fi]}.png"))
        for st in sheet_times:
            if fi == int(st * FPS):
                sheet[st] = fr.resize((W // 3, H // 3))
    p.stdin.close()
    p.wait()
    os.remove(wav)
    if sheet:
        cs = Image.new("RGB", (len(sheet) * W // 3, H // 3), (40, 40, 40))
        for i, st in enumerate(sorted(sheet)):
            cs.paste(sheet[st], (i * W // 3, 0))
        cs.save(os.path.join(out_dir, f"{name}__sheet.png"))
    return mp4, e.total, e.problems


def render_cover(word, rest, out, band="FF5A22"):
    band = parse_color(band, {}, (255, 90, 34))
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f = F("ko", 130)
    asc, desc = f.getmetrics()
    lh = asc + desc
    gap = 18
    total = lh * 2 + gap
    y0 = (H - total) / 2
    w1 = tw(f, word)
    d.rectangle(((W - w1) / 2 - 28, y0 - 6, (W + w1) / 2 + 28, y0 + lh + 6), fill=band)
    d.text((W / 2, y0 + lh / 2), word, font=f, fill=(0, 0, 0), anchor="mm")
    d.text((W / 2, y0 + lh + gap + lh / 2), rest, font=f, fill=(255, 255, 255), anchor="mm")
    img.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episodes", nargs="?")
    ap.add_argument("--only", type=int, help="1~5 중 한 편만")
    ap.add_argument("--check", action="store_true", help="렌더 없이 레이아웃 검사만")
    ap.add_argument("--cover", nargs=2, metavar=("WORD", "REST"))
    ap.add_argument("--band", default="FF5A22")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    if a.cover:
        print(render_cover(a.cover[0], a.cover[1], a.out or "cover.png", a.band))
        return
    if not a.episodes:
        ap.error("episodes.json 경로가 필요합니다")
    data = json.load(open(a.episodes, encoding="utf-8"))
    mode = data["mode"]
    set_no = data["set"]
    cfg = data.get("colors", {})
    out_dir = os.path.join(os.path.dirname(os.path.abspath(a.episodes)), "out")
    print("폰트:", {k: os.path.basename(v) for k, v in FONT_PATHS.items()})
    bad = False
    for i, ep in enumerate(data["episodes"], 1):
        if a.only and i != a.only:
            continue
        if a.check:
            e = Episode(ep, cfg, mode)
            print(f"[{i}] {LEVELS[e.level-1]} {e.total:.1f}s", "OK" if not e.problems else "")
            for pr in e.problems:
                print("   ⚠", pr); bad = True
            continue
        mp4, total, problems = render_episode(ep, cfg, mode, out_dir, set_no, i)
        print(f"[{i}] {mp4} ({total:.1f}s)")
        for pr in problems:
            print("   ⚠", pr); bad = True
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
