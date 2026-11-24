import json, subprocess, os, re, sys

ROOT = __import__("os").environ.get("NEWS_ROOT","/home/user/verbgame/content/2026-11-23-cnn")
OUT = f"{ROOT}/02_bento"
os.makedirs(OUT, exist_ok=True)
EXP = json.load(open(f"{ROOT}/01_news/expressions.json"))

def lum(h):
    h = h.lstrip('#'); r, g, b = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    f = lambda c: c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def cr(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la+0.05)/(lb+0.05)

# cell roles: bg, term, mean, sub(example), ko(translation), hl, hlfg, line, chip, chipfg, tag(outline color), border
PAL = {
 1: dict(no=4, name="Midnight Ink / Azure Blue / Vermilion Orange", bg="#080F1B", head="#F4F8FB",
         pill="#329DD2", pillfg="#080F1B", pillshadow="rgba(0,0,0,.70)", pillhi="rgba(255,255,255,.45)", pilldark="rgba(10,60,100,.55)",
         A=dict(bg="#FF4C2B", term="#121212", mean="#080F1B", sub="#121212", ko="#121212", hl="#080F1B", hlfg="#FFFFFF",
                line="rgba(8,15,27,.35)", chip="#080F1B", chipfg="#FFFFFF", tag="#080F1B", border="none"),
         B=dict(bg="#F4F8FB", term="#080F1B", mean="#1A6C9C", sub="#121212", ko="#2A3546", hl="#1A6C9C", hlfg="#FFFFFF",
                line="rgba(8,15,27,.22)", chip="#1A6C9C", chipfg="#FFFFFF", tag="#1A6C9C", border="none"),
         C=dict(bg="#111C2E", term="#F4F8FB", mean="#329DD2", sub="#F4F8FB", ko="#C9D3E0", hl="#329DD2", hlfg="#080F1B",
                line="rgba(244,248,251,.28)", chip="#329DD2", chipfg="#080F1B", tag="#329DD2", border="2px solid #24344F")),
 2: dict(no=5, name="Grape Purple / Soft Lavender / Mango Yellow", bg="#4A388E", head="#FFFFFF",
         pill="#FFBF48", pillfg="#2E2260", pillshadow="rgba(20,10,50,.55)", pillhi="rgba(255,255,255,.55)", pilldark="rgba(160,100,0,.45)",
         A=dict(bg="#FFBF48", term="#2E2260", mean="#4A388E", sub="#1E1640", ko="#2E2260", hl="#4A388E", hlfg="#FFFFFF",
                line="rgba(46,34,96,.30)", chip="#2E2260", chipfg="#FFBF48", tag="#4A388E", border="none"),
         B=dict(bg="#CDC6E4", term="#2E2260", mean="#4A388E", sub="#1E1640", ko="#2E2260", hl="#4A388E", hlfg="#FFFFFF",
                line="rgba(46,34,96,.28)", chip="#4A388E", chipfg="#FFFFFF", tag="#4A388E", border="none"),
         C=dict(bg="#2E2260", term="#FFFFFF", mean="#FFBF48", sub="#F4F1FA", ko="#CDC6E4", hl="#FFBF48", hlfg="#2E2260",
                line="rgba(205,198,228,.30)", chip="#FFBF48", chipfg="#2E2260", tag="#FFBF48", border="2px solid #6A58AE")),
 3: dict(no=6, name="Sky Blue / Cloud White / Scarlet Red", bg="#2C99D6", head="#0B1A2A",
         pill="#D62529", pillfg="#FFFFFF", pillshadow="rgba(10,40,70,.45)", pillhi="rgba(255,255,255,.40)", pilldark="rgba(110,0,5,.50)",
         A=dict(bg="#D62529", term="#FFFFFF", mean="#F8FAFC", sub="#FFFFFF", ko="#FFFFFF", hl="#F8FAFC", hlfg="#A8141A",
                line="rgba(255,255,255,.40)", chip="#F8FAFC", chipfg="#A8141A", tag="#F8FAFC", border="none"),
         B=dict(bg="#F8FAFC", term="#12263A", mean="#D62529", sub="#12263A", ko="#33465A", hl="#D62529", hlfg="#FFFFFF",
                line="rgba(18,38,58,.22)", chip="#D62529", chipfg="#FFFFFF", tag="#D62529", border="none"),
         C=dict(bg="#12263A", term="#F8FAFC", mean="#4DB0E8", sub="#F8FAFC", ko="#C4D4E2", hl="#4DB0E8", hlfg="#0B1A2A",
                line="rgba(248,250,252,.28)", chip="#4DB0E8", chipfg="#0B1A2A", tag="#4DB0E8", border="none")),
}
for p in PAL.values(): p["D"] = p["A"]

TERM_HTML = {"05": "at the highest<br>level since", "09": "put ~<br>in jeopardy"}

TERM_SIZE = {"11": "font-size:49px"}  # nonessential: 54px is 334px wide > 308px cell
NBSP = ["센 수", "지장을 주다", "줄 수 있다", "아직 없다"]  # keep short tails off their own line
def glue(t):
    for k in NBSP: t = t.replace(k, k.replace(" ", "&nbsp;"))
    return t
POS = {"A": (48, 470, 580, "big"), "B": (652, 470, 380, "small"), "C": (48, 1027, 380, "small"), "D": (452, 1027, 580, "big")}

def check(card):
    p = PAL[card]; bad = []
    def t(name, a, b, need):
        r = cr(a, b)
        if r < need: bad.append(f"card{card} {name} {a} on {b} = {r:.2f} < {need}")
        return round(r, 2)
    res = {}
    res["head/bg"] = t("head", p["head"], p["bg"], 4.5)
    res["pill"] = t("pill", p["pillfg"], p["pill"], 4.5)
    for s in "ABC":
        c = p[s]
        res[f"{s}.term"] = t(f"{s}.term", c["term"], c["bg"], 3)
        res[f"{s}.mean"] = t(f"{s}.mean", c["mean"], c["bg"], 3)
        res[f"{s}.example"] = t(f"{s}.sub", c["sub"], c["bg"], 4.5)
        res[f"{s}.translation"] = t(f"{s}.ko", c["ko"], c["bg"], 4.5)
        res[f"{s}.highlight"] = t(f"{s}.hl", c["hlfg"], c["hl"], 4.5)
        res[f"{s}.chip"] = t(f"{s}.chip", c["chipfg"], c["chip"], 4.5)
        res[f"{s}.tag"] = t(f"{s}.tag", c["tag"], c["bg"], 4.5)
    res["C/bg"] = round(cr(p["C"]["bg"], p["bg"]), 2)
    return res, bad

def example_html(e, c):
    en = e["example_en"]; hl = e["highlight"]
    assert hl in en, (e["id"], hl)
    style = (f"color:{c['hlfg']};background:{c['hl']};border-radius:8px;padding:0 8px;"
             "-webkit-box-decoration-break:clone;box-decoration-break:clone")
    i = en.index(hl); j = i+len(hl)
    # glue trailing punctuation to the last highlighted word
    m = re.match(r"[.,!?;:]+", en[j:]); punct = m.group(0) if m else ""
    words = hl.split(" ")
    head = " ".join(words[:-1])
    inner = (head + " " if head else "") + f"<span class='nw'>{words[-1]}</span>"
    return en[:i] + f"<b style=\"{style}\">{inner}</b>" + punct + en[j+len(punct):]

def build(card):
    p = PAL[card]
    items = sorted([e for e in EXP if e["card"] == card], key=lambda e: "ABCD".index(e["slot"]))
    cells = []
    for n, e in enumerate(items, 1):
        s = e["slot"]; c = p[s]; x, y, w, size = POS[s]
        term = TERM_HTML.get(e["id"], e["term"])
        cls = "big" if size == "big" else ("long" if len(e["term"]) >= 9 else "small")
        term = term.replace("~", "<span class='tilde'>~</span>")
        cells.append(f"""
<div class="cell" id="cell{s}" style="left:{x}px;top:{y}px;width:{w}px;background:{c['bg']};border:{c['border']};{'box-sizing:border-box;' if True else ''}">
  <div class="top"><span class="chip" style="background:{c['chip']};color:{c['chipfg']}">{n:02d}</span>
  <span class="tag" style="color:{c['tag']};border-color:{c['tag']}">{e['type']}</span></div>
  <div class="term {cls}" style="color:{c['term']};{TERM_SIZE.get(e['id'],'')}">{term}</div>
  <div class="mean" style="color:{c['mean']}">{glue(e['meaning_ko'])}</div>
  <div class="line" style="background:{c['line']}"></div>
  <div class="en" style="color:{c['sub']}">{example_html(e, c)}</div>
  <div class="ko" style="color:{c['ko']}">{glue(e['example_ko'])}</div>
</div>""")
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>card {card:02d}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden}}
body{{background:{p['bg']};font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif;position:relative}}
.pillwrap{{position:absolute;left:0;right:0;top:226px;text-align:center}}
.pill{{display:inline-block;border-radius:999px;padding:14px 44px;font-size:32px;font-weight:900;letter-spacing:2px;line-height:1.2;
  background:{p['pill']};color:{p['pillfg']};
  box-shadow:0 16px 30px {p['pillshadow']},inset 7px 7px 14px {p['pillhi']},inset -9px -9px 16px {p['pilldark']}}}
.title{{position:absolute;left:52px;top:330px;font-size:68px;font-weight:900;color:{p['head']};letter-spacing:-1px;line-height:1.2}}
.cell{{position:absolute;height:533px;border-radius:44px;padding:34px 36px;display:flex;flex-direction:column;overflow:hidden}}
.top{{display:flex;align-items:center;gap:14px;flex-shrink:0}}
.chip{{font-size:30px;font-weight:900;line-height:1;padding:8px 16px;border-radius:999px}}
.tag{{font-size:26px;font-weight:800;line-height:1;padding:8px 18px;border-radius:999px;border:2.5px solid}}
.term{{font-weight:900;line-height:1.12;letter-spacing:-1.5px;margin-top:16px;flex-shrink:0}}
.term.big{{font-size:74px}} .term.small{{font-size:62px}} .term.long{{font-size:54px}}
.tilde{{font-weight:700;opacity:.75}}
.mean{{font-size:38px;font-weight:800;line-height:1.3;margin-top:6px;word-break:keep-all;flex-shrink:0}}
.line{{height:2px;flex-shrink:0;margin:18px 0 14px}}
.en{{font-size:31px;font-weight:700;line-height:1.62}}
.en b{{font-weight:800}}
.nw{{white-space:nowrap}}
.ko{{font-size:27px;font-weight:500;line-height:1.5;margin-top:4px;word-break:keep-all}}
.handle{{position:absolute;left:0;right:0;top:1588px;text-align:center;font-size:30px;font-weight:800;color:{p['head']};white-space:pre}}
</style></head><body>
<div class="pillwrap"><span class="pill">NEWS ENGLISH · CNN</span></div>
<div class="title">뉴스로 배우는 영어 4가지.</div>
{''.join(cells)}
<div class="handle">지나쌤영어  @jina.ssam_english</div>
<script>
const r={{}};
document.querySelectorAll('.cell').forEach(c=>{{
  const cb=c.getBoundingClientRect(); const pad=34;
  let maxBottom=0, maxRight=0;
  c.querySelectorAll('.term,.mean,.en,.ko,.line,.top').forEach(k=>{{const b=k.getBoundingClientRect();maxBottom=Math.max(maxBottom,b.bottom);maxRight=Math.max(maxRight,k.scrollWidth+b.left);}});
  r[c.id]={{overflowY:Math.round(maxBottom-(cb.bottom-pad)), overflowX:Math.round(maxRight-(cb.right-36)),
    termW:Math.round(c.querySelector('.term').scrollWidth), cellInner:Math.round(cb.width-72),
    enLines:Math.round(c.querySelector('.en').getBoundingClientRect().height/50.2)}};
}});
const pre=document.createElement('pre');pre.id='measure';pre.style.display='none';pre.textContent=JSON.stringify(r);document.body.appendChild(pre);
</script>
</body></html>"""
    path = f"{OUT}/card_{card:02d}.html"
    open(path, "w").write(html)
    return path, items

def chrome(args):
    return subprocess.run(["google-chrome", "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                           "--force-device-scale-factor=1", "--window-size=1080,1920"] + args,
                          capture_output=True, text=True, timeout=120)

cards_json = []
allbad = []
for card in (1, 2, 3):
    path, items = build(card)
    res, bad = check(card); allbad += bad
    dom = chrome(["--virtual-time-budget=3000", "--dump-dom", f"file://{path}"]).stdout
    m = re.search(r'<pre id="measure"[^>]*>(.*?)</pre>', dom, re.S)
    print(f"card {card} measure:", m.group(1) if m else "NONE")
    print(f"card {card} contrast:", res)
    chrome([f"--screenshot={OUT}/card_{card:02d}.png", f"file://{path}"])
    p = PAL[card]
    cards_json.append(dict(card=card, palette=p["no"], palette_name=p["name"],
        colors=dict(background=p["bg"], head_and_handle=p["head"], pill=dict(bg=p["pill"], text=p["pillfg"]),
                    **{f"cell_{s}": {k: v for k, v in p[s].items()} for s in "ABCD"}),
        contrast=res,
        slots={e["slot"]: e["id"] for e in items},
        html=f"card_{card:02d}.html", png=f"card_{card:02d}.png"))
json.dump(cards_json, open(f"{OUT}/cards.json", "w"), ensure_ascii=False, indent=1)
print("FAILS:", allbad)
