import re, json
VOFF = 0.25
TEMPO = 1.0

# (display unit) chunks: list of (start,end,text) of speech from silence analysis
SENTENCES = [
  dict(id=1, ko="누군가에게 다시 기회를 주기로 한다는 건,\n지난 상처를 묻어 두기로 하거나\n시간이 다 치료해 줬다고 스스로\n생각하기로 하는 마음이다.",
       chunks=[(0.10, 2.50, "When I decide to give someone a second chance,"), (2.67, 3.95, "I'm basically"),
               (4.07, 5.28, "choosing to bury the old wounds,"),
               (5.56, 5.84, "or"), (5.95, 8.01, "telling myself that time has healed them.")],
       display=[[0, 1, 2], [3, 4]],
       cards=[("give someone a second chance", "give someone a second chance", "다시 기회를 주다"),
              ("bury the old wounds", "bury the old wounds", "오래된 상처를 묻다"),
              ("time has healed", "time heals", "시간이 치유해 주다")],
       marks=[]),
  dict(id=2, ko="하지만 시간이 지날수록\n그 사람의 본성이 다시 드러난다.",
       chunks=[(8.61, 9.86, "But as time goes by,"), (10.08, 11.71, "their true colors come out again.")],
       display=[[0, 1]],
       cards=[("true colors", "true colors", "본성, 진짜 모습")]),
  dict(id=3, ko="그래서 똑같이 상처받으면\n다시는 돌아갈 수 없다.",
       chunks=[(12.20, 13.86, "And when I get hurt the same way,"), (14.17, 15.33, "there's no going back.")],
       display=[[0, 1]],
       cards=[("no going back", "there's no going back", "돌이킬 수 없다")]),
  dict(id=4, ko="사람은 변하지 않는다고들 하지만,\n그게 상대에게만 해당되는 말은 아니다.",
       chunks=[(15.99, 17.55, "They say people never change,"), (17.86, 19.44, "but that's not just about them.")],
       display=[[0, 1]],
       cards=[("people never change", "people never change", "사람은 안 변한다")]),
  dict(id=5, ko="나도 다르지 않겠지.",
       chunks=[(19.92, 21.06, "I guess I'm no different.")],
       cards=[("no different", "be no different", "다르지 않다")]),
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
