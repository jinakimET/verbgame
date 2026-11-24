#!/usr/bin/env python3
"""Zoom-in sync reels (ig-reel-sync-zoomin): one reel per bento card, 4 boxes zoom to centre in item order.
Usage: NEWS_ROOT=... python3 render_zoom.py [card numbers...]   (default 1 2 3)
Sync: item boundaries = audio/words.json segments (long pauses >0.9s between items) -> exact, no estimates.
Audio per card is cut from audio/voice_full.mp3. Bird via tools/bird.py (mouth from clip RMS).
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
    words = {w["id"]: w for w in json.load(open(f"{ROOT}/audio/words.json"))}
    ids = [f"{(card - 1) * 4 + k + 1:02d}" for k in range(4)]
    items = [(words[i]["segments"][0][0], words[i]["segments"][-1][1]) for i in ids]
    c0 = 0.0 if card == 1 else max(0.0, items[0][0] - 0.3)
    c1 = items[-1][1] + 0.5
    wav = f"{OUT}/_clip_{card:02d}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{c0:.3f}", "-t", f"{c1 - c0:.3f}",
                    "-i", f"{ROOT}/audio/voice_full.mp3", wav], check=True)
    dur = c1 - c0
    nfr = int(round((dur + 0.5) * FPS))
    env = bird.envelope(wav, FPS, nfr)
    loc = [(a - c0, b - c0) for a, b in items]
    zi = [max(0.0, a - 0.05) for a, _ in loc]
    ze = [b + 0.03 for _, b in loc]
    zo = [min(0.35, max(0.15, (zi[k + 1] - ze[k]) if k < 3 else 0.35)) for k in range(4)]
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
        if t < ze[k]: return ease((t - zi[k]) / 0.40)
        return 1 - ease((t - ze[k]) / zo[k])

    outp = f"{OUT}/zoom_card_{card:02d}.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-shortest", outp], stdin=subprocess.PIPE)
    marks = {f"zoom{k + 1}": int(round((zi[k] + 0.4 + ze[k]) / 2 * FPS)) for k in range(4)}
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
    os.remove(wav); os.remove(f"{OUT}/card_{card:02d}_hi.png")
    return outp, dur + 0.5, c0, [(round(zi[k], 2), round(ze[k] + zo[k], 2)) for k in range(4)]


if __name__ == "__main__":
    os.makedirs(FR, exist_ok=True)
    for c in [int(a) for a in sys.argv[1:]] or [1, 2, 3]:
        print(*render(c), flush=True)
