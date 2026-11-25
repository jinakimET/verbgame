#!/usr/bin/env python3
"""Zoom-in sync reels (ig-reel-sync-zoomin): one reel per bento card, 4 boxes zoom to centre in item order.
Usage: NEWS_ROOT=... python3 render_zoom.py [card numbers...]   (default 1 2 3)
Data: audio/words_zoom.json["0N"] {audio, words, items:[{item,start,end}]} (Scribe times, exact). Own mp3 used whole. Bird via tools/bird.py (mouth from clip RMS).
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.environ.get("NEWS_ROOT", "/home/user/verbgame/content/2026-11-23-cnn")
OUT = f"{ROOT}/04_zoom_reels"; FR = f"{OUT}/frames"
W, H, FPS = 1080, 1920, 30
S = 2.5
CELLS = [(48, 470, 580, 533), (652, 470, 380, 533), (48, 1027, 380, 533), (452, 1027, 580, 533)]
MAG = [1.65, 2.25, 2.25, 1.65]
TX, TY = 540, 900
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bird
bird.H_OUT = 200


def ease(x):
    x = min(1, max(0, x))
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def comp(fr, im, pos):
    lay = Image.new("RGBA", fr.size, (0, 0, 0, 0)); lay.paste(im, pos); fr.alpha_composite(lay)


def capture(card):
    hi = f"{OUT}/card_{card:02d}_hi.png"
    subprocess.run(["google-chrome", "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={S}", "--window-size=1080,1920", f"--screenshot={hi}",
                    f"file://{ROOT}/02_bento/card_{card:02d}.html"], check=True, capture_output=True)
    return Image.open(hi).convert("RGB")


def render(card):
    """Data-driven: audio/words_zoom.json["0N"] = {audio, words:[{t,s,e}], items:[{item,start,end}]} (exact Scribe times, s).
    The card's own mp3 is used whole; item k -> box A,B,C,D. Video = audio + 0.5s."""
    cfg = json.load(open(f"{ROOT}/audio/words_zoom.json"))[f"{card:02d}"]
    wav = f"{ROOT}/audio/{cfg['audio']}"
    adur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
                                capture_output=True, text=True, check=True).stdout)
    items = sorted(cfg["items"], key=lambda i: i["item"])
    loc = [(i["start"], min(i["end"], adur)) for i in items]
    dur = adur
    nfr = int(round((dur + 0.5) * FPS))
    env = bird.envelope(wav, FPS, nfr)
    zi = [max(0.0, a - 0.05) for a, _ in loc]      # zoom start
    ze = [b + 0.03 for _, b in loc]                # return start
    zin = [0.40] * 4                               # zoom-in duration
    zo = [0.35] * 4                                # return duration
    for k in range(3):                             # tight handover: return fully ends before next zoom starts
        gap = zi[k + 1] - ze[k]
        if gap < 0.35 + 0.0:
            if gap >= 0.15:
                zo[k] = gap
            else:                                  # return starts a little early (inside the last word's tail), 0.15s
                zo[k] = 0.15; ze[k] = zi[k + 1] - 0.15
                if k + 1 < 4: zin[k + 1] = 0.28
        if zi[k + 1] - ze[k] - zo[k] < -1e-6: raise SystemExit("overlap")
    zo[3] = 0.35
    hi = capture(card)
    bg = hi.resize((W, H), Image.LANCZOS)
    black = Image.new("RGB", (W, H), (0, 0, 0))
    cells = []
    for (x, y, w, h) in CELLS:
        c = hi.crop((int(x * S), int(y * S), int((x + w) * S), int((y + h) * S))).convert("RGBA")
        m = Image.new("L", c.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), 44 * S, fill=255)
        c.putalpha(m); cells.append(c)

    def prog(k, t):
        if t < zi[k] or t >= ze[k] + zo[k]: return 0.0
        if t < ze[k]: return ease((t - zi[k]) / zin[k])
        return 1 - ease((t - ze[k]) / zo[k])

    outp = f"{OUT}/zoom_card_{card:02d}.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-shortest", outp], stdin=subprocess.PIPE)
    marks = {f"zoom{k + 1}": int(round((zi[k] + zin[k] + ze[k]) / 2 * FPS)) for k in range(4)}
    marks["base"] = int(round((ze[3] + zo[3] + 0.15) * FPS))
    want = {v: n for n, v in marks.items()}
    sheet = {}
    for f in range(nfr):
        t = f / FPS
        k, pr = max(((k, prog(k, t)) for k in range(4)), key=lambda a: a[1])
        fr = (Image.blend(bg, black, 0.62 * pr) if pr > 0 else bg.copy()).convert("RGBA")
        if pr > 0:
            x, y, w, h = CELLS[k]; mg = 1 + (MAG[k] - 1) * pr
            cx = (x + w / 2) + (TX - (x + w / 2)) * pr; cy = (y + h / 2) + (TY - (y + h / 2)) * pr
            nw, nh = int(round(w * mg)), int(round(h * mg))
            px, py = int(round(cx - nw / 2)), int(round(cy - nh / 2))
            pad = 100
            sh = Image.new("RGBA", (nw + 2 * pad, nh + 2 * pad), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 12, pad + nw, pad + nh + 12), 44 * mg,
                                                 fill=(0, 0, 0, int(150 * pr)))
            comp(fr, sh.filter(ImageFilter.GaussianBlur(30)), (px - pad, py - pad))
            comp(fr, cells[k].resize((nw, nh), Image.BICUBIC), (px, py))
        bird.place(fr, float(env[min(f, len(env) - 1)]), 540, 1890)
        rgb = fr.convert("RGB")
        if f in want: sheet[want[f]] = rgb.copy()
        p.stdin.write(rgb.tobytes())
    p.stdin.close(); p.wait()
    tw, th = 360, 640
    cs = Image.new("RGB", (tw * 5 + 60, th + 20), (30, 30, 30))
    for i, n in enumerate(["base", "zoom1", "zoom2", "zoom3", "zoom4"]):
        cs.paste(sheet[n].resize((tw, th), Image.LANCZOS), (10 + i * (tw + 10), 10))
        sheet[n].save(f"{FR}/check_{card:02d}_{n}.png")
    cs.save(f"{FR}/check_{card:02d}_sheet.png")
    os.remove(f"{OUT}/card_{card:02d}_hi.png")
    return outp, dur + 0.5, [(round(zi[k], 2), round(ze[k] + zo[k], 2)) for k in range(4)]


if __name__ == "__main__":
    os.makedirs(FR, exist_ok=True)
    for c in [int(a) for a in sys.argv[1:]] or [1, 2, 3]:
        print(*render(c), flush=True)
