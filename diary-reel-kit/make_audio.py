# 사용: python3 make_audio.py   (render.py의 DUR, voice.mp3, render3 arrivals 사용)
# bgm.wav + voice_pad.wav + sfx5.wav -> 덕킹 믹스 -> -14 LUFS -> mix5.wav
import subprocess, re, json, wave, os, sys
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)) + "/"
os.chdir(ROOT)
src = open("render.py").read()
DUR = float(re.search(r"W, H, FPS, DUR = \d+, \d+, \d+, ([\d.]+)", src).group(1))
b = open("bgm.py").read()
b = re.sub(r"DUR = [\d.]+", f"DUR = {DUR}", b); open("bgm.py", "w").write(b)
subprocess.run([sys.executable, "bgm.py"], check=True)
ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
subprocess.run(ff + ["-i", "voice.mp3", "-af", f"adelay=250|250,apad=whole_dur={DUR},aresample=44100,pan=stereo|c0=c0|c1=c0",
                     "-t", str(DUR), "voice_pad.wav"], check=True)
arr = json.loads(subprocess.run([sys.executable, "render3.py", "arrivals"], capture_output=True, text=True).stdout.strip())
SR = 44100; n = int(SR * DUR); out = np.zeros(n)
for t0 in arr:  # "뿅" pop: 짧은 상승 스윕 + 반짝임
    L = int(0.18 * SR); tt = np.arange(L) / SR
    f = 500 + 1400 * tt / 0.18
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 22) + 0.3 * np.sin(2 * np.pi * 2600 * tt) * np.exp(-tt * 40)
    i = int(t0 * SR); out[i:i + L] += s[: max(0, min(L, n - i))]
out = out / (np.abs(out).max() + 1e-9) * 0.8
with wave.open("sfx5.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.stack([out, out], 1) * 32767).astype(np.int16).tobytes())
fc = ("[0:a]volume=0.55[b];[1:a]asplit[v][sc];[b][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[bd];"
      "[2:a]volume=0.35[fx];[bd][v][fx]amix=inputs=3:normalize=0:duration=longest[m]")
subprocess.run(ff + ["-i", "bgm.wav", "-i", "voice_pad.wav", "-i", "sfx5.wav", "-filter_complex", fc, "-map", "[m]",
                     "-t", str(DUR), "pre5.wav"], check=True)
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", "pre5.wav", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
subprocess.run(ff + ["-i", "pre5.wav", "-af", f"volume={-14 - I:.2f}dB,alimiter=limit=0.89:level=false", "mix5.wav"], check=True)
print("mix5.wav ok, cards at", arr, "| LUFS before", I)
