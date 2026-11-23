#!/usr/bin/env python3
"""Keyword (ig-reel) reels: adapts render_expr_reels.py visuals; audio = audio/kw_NN.mp3, timing = audio/words_kw.json.
Usage: NEWS_ROOT=... python3 render_kw_reels.py [01 07 09]"""
import json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_expr_reels as R
from render_expr_reels import *

OUT = f"{ROOT}/06_keyword_reels"; FR = f"{OUT}/frames"
TAIL = 0.8
_orig_wrap = R.wrap_example
def _bal_wrap(tokens, split, hl_idx, f, maxw):
    base = _orig_wrap(tokens, split, hl_idx, f, maxw); out = []
    for k in (0, 1):
        n = sum(1 for p, _ in base if p == k)
        if n == 0: continue
        lo, hi = 200, maxw
        while hi - lo > 4:
            mid = (lo + hi) // 2
            if sum(1 for p, _ in _orig_wrap(tokens, split, hl_idx, f, mid) if p == k) == n: hi = mid
            else: lo = mid
        out += [x for x in _orig_wrap(tokens, split, hl_idx, f, hi) if x[0] == k]
    return out
R.wrap_example = _bal_wrap
CARD = {"01": 1, "07": 2, "09": 3, "05": 2, "11": 3}
scripts = {r["id"]: r for r in J("03_script/keyword_scripts.json")["reels"]}
WK = J("audio/words_kw.json")

def build_kw(rid):
    sc = scripts[rid]; wk = WK[rid]; words = wk["words"]
    card = {c["card"]: c for c in J("02_bento/cards.json")}[CARD[rid]]
    cc = card["colors"]["cell_C"]
    white, mean, dim = hexrgb(cc["term"]), hexrgb(cc["mean"]), hexrgb(cc["ko"])
    hlbg, hlfg = hexrgb(cc["hl"]), hexrgb(cc["hlfg"])
    term = sc["term"]; cy = (PY0 + PY1) // 2
    beats = []; marks = {}
    def bt(i): return wk["beats"][i]["start"]
    for i, b in enumerate(sc["beats"]):
        role, txt = b["role"], b["on_screen"]; t0 = bt(i)
        assert wk["beats"][i]["role"] == role
        bw = words[wk["beats"][i]["first_word_idx"]:][:wk["beats"][i]["n_words"]]
        if role == "hook":
            f, lines = fit_lines(txt, FB, 100, TEXT_W, 2)
            q = chip("오늘의 CNN 표현", hlbg, hlfg); T = -FADE   # fully visible at frame 0
            beats.append((0.0, stack([(q, T), (text_sprite(lines, f, white), T)], cy, 48), []))
            marks["hook"] = 0.2
        elif role == "stake":
            f, lines = fit_lines(txt, FB, 92, TEXT_W, 1, 64)
            if len(lines) > 1 or text_size(f, lines[0])[0] > TEXT_W: f, lines = fit_lines(txt, FB, 92, TEXT_W, 2)
            beats.append((t0, stack([(text_sprite(lines, f, white), t0)], cy, 40), []))
        elif role == "term":
            f, lines = fit_lines(term, FB, 120, TEXT_W, 1, 56)
            beats.append((t0, stack([(chip("표현" if " " in term else "단어", hlbg, hlfg), t0),
                                     (text_sprite(lines, f, white), t0)], cy, 44), []))
        elif role == "meaning":
            ko = txt.split("=")[-1].strip()
            f, lines = fit_lines(term, FB, 112, TEXT_W, 1, 56)
            fm, ml = fit_lines(ko, FB, 76, TEXT_W, 2)
            beats.append((t0, stack([(text_sprite(lines, f, white), t0), (text_sprite(ml, fm, mean), t0 + 0.2)], cy, 44), []))
        elif role == "example_en":
            toks = txt.split(); hl = b["highlight"].split()
            nt = [norm(t) for t in toks]; hi = next(i for i in range(len(nt)) if nt[i:i+len(hl)] == [norm(x) for x in hl])
            split = {"01": 5, "07": 3, "09": 4, "05": 2, "11": 2}[rid]
            hl_idx = (hi, hi + len(hl))
            tw = lambda k: bw[k]["s"]
            size = 72; maxl = {"01": 2, "07": 2, "09": 3, "05": 3, "11": 2}[rid]; floor = 44 if rid not in ("09", "05") else 52
            while True:
                fe = font(FBOLD, size)
                exs = example_sprites(toks, split, hl_idx, fe, white, hlbg, hlfg, TEXT_W - 30)
                if (len(exs) <= maxl and max(s.width for _, s, _ in exs) <= TEXT_W) or size <= floor: break
                size -= 4
            tpart = [t0, tw(split) - 0.05]
            items = [(chip("예문", hlbg, hlfg), t0)] + [(s, tpart[pi]) for pi, s, _ in exs]
            els = stack(items, cy, 18)
            th = tw(hi) - 0.05
            boxes = [(bx, els[i + 1], th) for i, (pi, s, bx) in enumerate(exs) if bx]
            beats.append((t0, els, boxes))
            marks["example_en"] = tw(len(toks) - 2)
        elif role == "example_ko":
            fk, kl = fit_lines(txt, FB, 72, TEXT_W, 3)
            en = [x for x in sc["beats"] if x["role"] == "example_en"][0]["on_screen"]
            fs, sl = fit_lines(en, FMED, 38, TEXT_W, 2, 30)
            beats.append((t0, stack([(chip("해석", hlbg, hlfg), t0), (text_sprite(kl, fk, white, 1.3), t0),
                                     (text_sprite(sl, fs, dim), t0 + 0.2)], cy, 40), []))
            marks["example_ko"] = (t0 + bt(i + 1)) / 2
        elif role == "payoff_loop":
            fo, ol = fit_lines(txt, FB, 100, TEXT_W, 2)
            ft, tl = fit_lines(term, FB, 80, TEXT_W - 40, 1, 40)
            ts = text_sprite(tl, ft, hlfg)
            box = Image.new("RGBA", (ts.width + 40, ts.height + 24), (0, 0, 0, 0))
            ImageDraw.Draw(box).rounded_rectangle((0, 0, box.width - 1, box.height - 1), 14, fill=hlbg + (255,))
            box.alpha_composite(ts, (20, 8))
            beats.append((t0, stack([(text_sprite(ol, fo, white), t0), (box, t0 + 0.15)], cy, 50), []))
            marks["payoff"] = min(t0 + 1.0, words[-1]["s"])
    last = words[-1]["e"]
    total = round((last + TAIL) * FPS) / FPS
    return dict(beats=beats, total=total, card=card, marks=marks, last=last)

def mouth(rid, total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", f"{ROOT}/audio/kw_{rid}.mp3", "-ac", "1", "-ar", "8000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64)
    spf = 8000 / FPS; n = int(len(x) / spf)
    rms = np.array([np.sqrt(np.mean(x[int(i*spf):int((i+1)*spf)] ** 2)) for i in range(n)])
    v = np.clip(rms / (np.percentile(rms, 90) or 1), 0, 1) ** 0.8; v[v < 0.08] = 0
    env = np.zeros(int(round(total * FPS)) + 2); prev = 0.0
    for i in range(len(env)):
        tgt = v[i] if i < n else 0.0
        prev = tgt if tgt >= prev else prev * 0.6
        if prev < 0.02: prev = 0.0
        env[i] = prev
    return env

def render_kw(rid):
    Rd = build_kw(rid); base = make_base(Rd["card"]); os.makedirs(FR, exist_ok=True)
    out = f"{OUT}/kw_{rid}.mp4"; nfr = int(round(Rd["total"] * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", f"{ROOT}/audio/kw_{rid}.mp3", "-filter_complex", "[1:a]apad,aformat=channel_layouts=stereo[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-threads", "2", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-t", f"{Rd['total']:.3f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE); env = mouth(rid, Rd["total"])
    for i in range(nfr):
        p.stdin.write(frame(base, Rd, i / FPS, env[i]).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError(rid)
    for k, t in Rd["marks"].items():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", out, "-frames:v", "1", f"{FR}/kw_{rid}_{k}.png"], check=True)
    print(rid, Rd["total"], Rd["marks"], flush=True)

if __name__ == "__main__":
    for r in sys.argv[1:] or ["01", "07", "09"]: render_kw(r)
