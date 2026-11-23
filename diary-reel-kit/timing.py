import re, json
VOFF = 0.25
TEMPO = 1.0

# (display unit) chunks: list of (start,end,text) of speech from silence analysis
SENTENCES = [
  dict(id=1, ko="SNS에서 화려한 릴스들을 보면\n어떻게 이런 아이디어를 떠올리나 싶다.",
       chunks=[(0.05, 1.67, "Scrolling through social media,"), (1.77, 2.90, "I see so many"),
               (3.02, 4.05, "dazzling reels,"),
               (4.52, 6.90, "and I wonder how people come up with such ideas.")],
       display=[[0, 1, 2], [3]],
       cards=[("scrolling through", "scroll through", "훑어보다, 스크롤하다"),
              ("come up with", "come up with", "(아이디어를) 떠올리다")],
       marks=["dazzling reels"]),
  dict(id=2, ko="잠시 내가 작게 느껴진다.",
       chunks=[(7.42, 9.18, "They make me feel small for a moment.")],
       cards=[("feel small", "make someone feel small", "작아지게 만들다")]),
  dict(id=3, ko="하지만 결국 AI를 얼마나 잘 쓰느냐의\n차이라는 생각이 든다.",
       chunks=[(9.76, 13.77, "But then I remind myself that a lot of it comes down to how well you use AI.")],
       cards=[("comes down to", "come down to ~", "결국 ~의 문제로 귀결되다")]),
  dict(id=4, ko="몇 년째 AI 공부를 열심히 해 왔는데,\n정말 편한 세상이다.",
       chunks=[(14.32, 16.76, "I've been studying AI hard for years now,"), (17.04, 18.78, "and what a convenient world it is.")],
       display=[[0, 1]], cards=[], marks=["convenient world"]),
  dict(id=5, ko="이 일기는 내 생각이고,\n영상과 편집은 AI가 맡아 준다.",
       chunks=[(19.33, 21.13, "These diary entries are my own thoughts,"), (21.49, 23.54, "while AI handles the video and editing.")],
       display=[[0, 1]],
       cards=[("handles", "handle ~", "~을 맡아서 처리하다")],
       marks=["my own thoughts"]),
  dict(id=6, ko="내용이 같다면 포장이 예쁜 것에 돈을 쓰니,\n나만의 가치를 어떻게 가꿀지 계속 고민해 보려 한다.",
       chunks=[(24.11, 25.43, "When the content is the same,"), (25.62, 27.23, "people pay for nicer packaging,"),
               (27.55, 30.97, "so I plan to keep thinking about how to cultivate my own value.")],
       display=[[0, 1], [2]],
       cards=[("pay for nicer packaging", "pay for nicer packaging", "포장에 돈을 쓰다"),
              ("cultivate my own value", "cultivate one's value", "자신의 가치를 가꾸다")]),
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
