import re, json
VOFF = 0.25
TEMPO = 1.0

# (display unit) chunks: list of (start,end,text) of speech from silence analysis
SENTENCES = [
  dict(id=1, ko="내가 만나는 사람이 좋은 사람인지 아닌지는\n사실 그렇게 중요하지 않다고 한다.",
       chunks=[(0.05, 3.71, "They say it doesn't really matter whether the person I meet is good or not.")],
       cards=[("doesn't really matter", "doesn't really matter", "별로 중요하지 않다")]),
  dict(id=2, ko="그 사람이 좋은 사람이어도, 만나고 돌아왔을 때\n기분이 찜찜하고, 나다운 모습을 유지하지 못했고,\n나도 모르게 불편함을 감수하고 있었다면\n그 사람은 나에게 좋은 사람이 아니다.",
       chunks=[(4.20, 5.62, "Even if they're a good person,"), (5.89, 7.54, "if I come home feeling uneasy,"),
               (7.94, 9.33, "if I couldn't be myself,"), (9.74, 12.40, "if I was putting up with discomfort without realizing it,"),
               (12.77, 14.46, "then they're not a good person for me.")],
       display=[[0, 1], [2, 3], [4]],
       cards=[("feeling uneasy", "feel uneasy", "찜찜하다, 마음이 불편하다"),
              ("be myself", "be myself", "나답게 있다"),
              ("putting up with", "put up with", "참고 견디다"),
              ("without realizing it", "without realizing it", "나도 모르게")]),
  dict(id=3, ko="생각해 보니 몇 년을 부부로 지내도\n배우자와 있을 때 내가 진정으로 편한지\n판단하기 어려웠다.",
       chunks=[(15.31, 16.21, "Come to think of it,"), (16.45, 18.20, "even after years of marriage,"),
               (18.38, 21.62, "it was hard to tell if I was truly comfortable around my spouse.")],
       display=[[0, 1, 2]],
       cards=[("come to think of it", "come to think of it", "생각해 보니")]),
  dict(id=4, ko="그래서 상대를 아는 것보다\n나 자신을 아는 것이 더 중요하다고 생각한다.",
       chunks=[(22.10, 25.73, "So I think knowing myself matters more than knowing the other person.")],
       cards=[("matters more than", "matter more than", "~보다 더 중요하다")]),
]

def syl(w):
    w = re.sub(r"[^a-z']", "", w.lower())
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"): n -= 1
    return max(1, n)

def build():
    out = []
    for s in SENTENCES:
        words = []
        for ci, (a, b, txt) in enumerate(s["chunks"]):
            a, b = a / TEMPO, b / TEMPO
            toks = txt.split()
            wts = [syl(t) + 0.6 + (0.35 if t[-1] in ",.?" else 0) for t in toks]
            tot = sum(wts); t = a
            for tok, wt in zip(toks, wts):
                d = (b - a) * wt / tot
                words.append(dict(w=tok, s=t + VOFF, e=t + d + VOFF, chunk=ci))
                t += d
        # map cards to word index ranges
        cards = []
        for key, en, ko in s["cards"]:
            kt = key.lower().split()
            low = [re.sub(r"[^a-z']", "", w["w"].lower()) for w in words]
            for i in range(len(low)):
                if low[i:i + len(kt)] == [re.sub(r"[^a-z']", "", k) for k in kt]:
                    cards.append(dict(en=en, ko=ko, i0=i, i1=i + len(kt) - 1,
                                      t=words[i]["s"]))
                    break
            else:
                raise SystemExit("card phrase not found: " + key)
        marks = []
        low = [re.sub(r"[^a-z']", "", w["w"].lower()) for w in words]
        for key in s.get("marks", []):
            kt = [re.sub(r"[^a-z']", "", k) for k in key.lower().split()]
            for i in range(len(low)):
                if low[i:i + len(kt)] == kt: marks.append((i, i + len(kt) - 1))
        disp = s.get("display", [[i for i in range(len(s["chunks"]))]])
        units = []
        for g in disp:
            idx = [i for i, w in enumerate(words) if w["chunk"] in g]
            units.append(dict(idx=idx, s=words[idx[0]]["s"], e=words[idx[-1]]["e"]))
        out.append(dict(id=s["id"], ko=s["ko"], big=s.get("big", False), words=words,
                        cards=cards, units=units, marks=marks,
                        s=words[0]["s"], e=words[-1]["e"]))
    return out

_build0 = build
def build():
    out = _build0()
    allc = sorted([c for s_ in out for c in s_["cards"]], key=lambda c: c["t"])
    for a_, b_ in zip(allc, allc[1:]):
        if b_["t"] - a_["t"] < 1.4: b_["t"] = a_["t"] + 1.4
    return out

if __name__ == "__main__":
    for s in build():
        print(s["id"], round(s["s"], 2), round(s["e"], 2), [(c["en"], round(c["t"], 2)) for c in s["cards"]])
