import numpy as np, wave
SR = 44100
DUR = 37.0
t = np.arange(int(SR * DUR)) / SR
def hz(n): return 440 * 2 ** ((n - 69) / 12)
# Fmaj7  Em7  Dm7  Cmaj7  (midi notes), 2 bars each at 80bpm -> 3s per chord
chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]
CH = 3.0
pad = np.zeros_like(t); pl = np.zeros_like(t)
for k in range(int(DUR / CH) + 1):
    ch = chords[k % 4]; t0 = k * CH
    m = (t >= t0) & (t < t0 + CH + 0.6)
    tt = t[m] - t0
    env = np.minimum(1, tt / 0.8) * np.exp(-np.maximum(0, tt - CH) / 0.25)
    for n in ch:
        f = hz(n)
        pad[m] += env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt + 0.3)
                         + 0.15 * np.sin(2 * np.pi * f * 1.003 * tt))
    # soft pluck arpeggio, eighth notes
    arp = ch + [ch[2] + 12, ch[1] + 12, ch[3]]
    for j in range(8):
        n = arp[j % len(arp)] + 12
        s = t0 + j * CH / 8
        mm = (t >= s) & (t < s + 1.2)
        ttt = t[mm] - s
        pl[mm] += np.exp(-ttt * 5) * np.sin(2 * np.pi * hz(n) * ttt) * (1 - np.exp(-ttt * 200))
    # bass
    mb = (t >= t0) & (t < t0 + CH)
    tb = t[mb] - t0
    pad[mb] += 1.2 * np.minimum(1, tb / 0.05) * np.exp(-tb * 0.8) * np.sin(2 * np.pi * hz(ch[0] - 12) * tb)
mix = 0.10 * pad + 0.16 * pl
# gentle lowpass via moving average
k = 6; mix = np.convolve(mix, np.ones(k) / k, mode="same")
fade = np.minimum(1, t / 0.4) * np.minimum(1, (DUR - t) / 0.6)
mix *= fade
mix = mix / np.abs(mix).max() * 0.5
st = np.stack([mix, np.roll(mix, 300)], 1)
with wave.open(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/bgm.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok")
