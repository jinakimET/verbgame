#!/usr/bin/env python3
"""한글 기사 캐러셀 렌더(네오브루탈리즘). 사용: NEWS_ROOT=content/<날짜>-<slug> python3 build_carousel.py
입력 03_script/carousel_copy.json, 출력 07_carousel/slide_00_cover.png, slide_01~05.png(+html), contact_sheet.png"""
import os, sys, json, re, io, base64, html, subprocess, shutil, tempfile
from PIL import Image

ROOT = os.environ.get("NEWS_ROOT") or sys.exit("NEWS_ROOT 환경변수가 필요하다")
ROOT = os.path.abspath(ROOT)
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = f"{ROOT}/07_carousel"
os.makedirs(OUT, exist_ok=True)
copy = json.load(open(f"{ROOT}/03_script/carousel_copy.json"))

# ---- 팔레트 11번(Jet Black / Hot Pink / Chartreuse) + near-black / off-white
PAL_NO = 11
INK, PINK, LIME, PAPER = "#151515", "#FF2DA8", "#D4FF3F", "#FFF8EC"

def lum(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
def cr(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)
PAIRS = {  # (글자색, 배경색, 종류, 기준)
    "표현 큰 글자 ink/pink": (INK, PINK, "large", 3), "표현 큰 글자 ink/lime": (INK, LIME, "large", 3),
    "표현 큰 글자 ink/paper": (INK, PAPER, "large", 3), "표지 제목 lime/ink": (LIME, INK, "large", 3),
    "본문 ink/paper": (INK, PAPER, "body", 4.5), "본문 ink/lime": (INK, LIME, "body", 4.5),
    "본문 ink/pink": (INK, PINK, "body", 4.5), "뜻 태그 lime/ink": (LIME, INK, "body", 4.5),
    "핸들 paper/ink": (PAPER, INK, "body", 4.5),
}
contrast = {}
for k, (f, b, kind, need) in PAIRS.items():
    v = cr(f, b); contrast[k] = round(v, 2)
    assert v >= need, f"대비 미달 {k} {v:.2f}"

# ---- 팔레트 기록
copy["palette"] = [PAL_NO]
json.dump(copy, open(f"{ROOT}/03_script/carousel_copy.json", "w"), ensure_ascii=False, indent=1)
pu_path = f"{REPO}/content/palettes_used.json"
pu = json.load(open(pu_path))
if PAL_NO not in pu["used"]:
    pu["used"].append(PAL_NO)
    pu["note"] += " 11/25 한글기사 캐러셀(kr-exam-ai): 11(핫핑크·차트루즈·잉크, 네오브루탈리즘)."
    json.dump(pu, open(pu_path, "w"), ensure_ascii=False, indent=1)

# ---- 새(입 벌린 포즈)
sys.path.insert(0, os.path.dirname(__file__))
_so = sys.stdout; sys.stdout = io.StringIO()
import bird as _bird
sys.stdout = _so
_im = _bird.mouth(1.0)
_buf = io.BytesIO(); _im.save(_buf, "PNG")
BIRD = "data:image/png;base64," + base64.b64encode(_buf.getvalue()).decode()
BIRD_R = _im.width / _im.height

E = lambda s: html.escape(s)

# ---- 선형 일러스트(SVG). 선 6px near-black, 채움 최소
S = f'fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"'
def svg(vb, body, w, h, extra=""):
    return f'<svg viewBox="0 0 {vb[0]} {vb[1]}" width="{w}" height="{h}" {S} {extra}>{body}</svg>'

ILL = {}
ILL["cover"] = (560, 440, f'''
<g transform="rotate(-6 150 240)"><rect x="50" y="130" width="210" height="270" rx="8" fill="{PAPER}"/>
<path d="M80 180h110M80 225h150M80 270h130M80 315h150"/><circle cx="215" cy="180" r="12" fill="{PINK}"/></g>
<rect x="340" y="230" width="150" height="150" rx="16" fill="{LIME}"/><rect x="380" y="270" width="70" height="70" rx="8"/>
<path d="M370 230v-26M410 230v-26M450 230v-26M370 380v26M410 380v26M450 380v26M340 270h-26M340 310h-26M340 350h-26M490 270h26M490 310h26M490 350h26"/>
<path d="M255 300c25-30 30 30 55 0" />
<g fill="{PAPER}"><path d="M40 30h130a14 14 0 0 1 14 14v46a14 14 0 0 1-14 14h-70l-28 24v-24h-32a14 14 0 0 1-14-14V44a14 14 0 0 1 14-14z"/>
<path d="M215 10h120a14 14 0 0 1 14 14v40a14 14 0 0 1-14 14h-14v22l-26-22h-80a14 14 0 0 1-14-14V24a14 14 0 0 1 14-14z"/>
<path d="M385 50h130a14 14 0 0 1 14 14v40a14 14 0 0 1-14 14h-30l-22 20v-20h-78a14 14 0 0 1-14-14V64a14 14 0 0 1 14-14z" fill="{PINK}"/></g>
<path d="M62 70h90M62 90h60M235 40h90M235 58h50M410 80h90"/>''')
ILL[1] = (420, 340, f'''
<path d="M10 300h400"/>
<path d="M40 295l62-130h236l-62 130z" fill="{PAPER}"/>
<path d="M120 200h150M105 235h150M90 270h100"/>
<rect x="318" y="100" width="62" height="46" rx="8" fill="{PINK}" transform="rotate(-8 349 123)"/><circle cx="349" cy="123" r="12" fill="{PAPER}"/><circle cx="349" cy="123" r="3" fill="{INK}"/>
<path d="M200 215l90-30" stroke-width="10"/><path d="M290 185l22-7" stroke-width="10" stroke="{PINK}"/>
<path d="M96 66L210 160L80 176z" fill="{LIME}"/>
<rect x="14" y="34" width="86" height="34" rx="8" fill="{PAPER}" transform="rotate(28 57 51)"/>
<circle cx="230" cy="46" r="30" fill="{PAPER}"/><circle cx="310" cy="46" r="30" fill="{PAPER}"/>
<circle cx="224" cy="54" r="11" fill="{INK}"/><circle cx="304" cy="54" r="11" fill="{INK}"/>
<path d="M200 8l50 12M340 8l-50 12"/>''')
ILL[2] = (420, 340, f'''
<path d="M20 300a170 170 0 0 1 340 0z" fill="{PAPER}"/>
<path d="M60 300a130 130 0 0 1 260 0M100 300a90 90 0 0 1 180 0M140 300a50 50 0 0 1 100 0"/>
<path d="M190 300L340 180A190 190 0 0 0 190 130z" fill="{LIME}"/>
<path d="M190 300V120"/>
<circle cx="290" cy="170" r="22" fill="{PINK}"/><circle cx="290" cy="170" r="7" fill="{PAPER}"/>
<circle cx="290" cy="170" r="54" fill="none"/><path d="M328 208l60 66"/>''')
ILL[3] = (420, 340, f'''
<path d="M10 30h400M10 30v300"/>
<g transform="rotate(30 90 80)"><rect x="40" y="55" width="110" height="50" rx="10" fill="{PAPER}"/><circle cx="150" cy="80" r="16" fill="{PINK}"/></g>
<path d="M42 20l-14 40"/>
<path d="M165 120L300 330H120z" fill="{LIME}"/>
<path d="M300 330H410V120L225 138z" fill="{INK}"/>
<path d="M240 250l55-70M270 300l95-120M330 320l60-90" stroke="{PAPER}" stroke-width="4" stroke-dasharray="2 14"/>''')
ILL[4] = (420, 340, f'''
<path d="M10 305h400"/>
<g transform="rotate(-28 190 120)"><rect x="150" y="30" width="150" height="86" rx="12" fill="{PINK}"/><path d="M190 30v86M260 30v86"/>
<path d="M225 116v140" stroke-width="16"/></g>
<rect x="215" y="250" width="170" height="55" rx="8" fill="{PAPER}"/>
<circle cx="260" cy="228" r="22" fill="{LIME}"/><path d="M282 228c30 0 36 22 20 22"/><rect x="320" y="200" width="42" height="34" rx="6"/>
<path d="M60 215l-34-10M70 250l-44 8M40 180l-26-26"/>''')
ILL[5] = (420, 340, f'''
<path d="M10 140h110v200H10zM300 140h110v200H300z" fill="{PAPER}"/>
<path d="M120 140h50l16 26-34 14 30 28M300 140h-40l-12 26 28 18"/>
<path d="M150 190l14 40-22 30M255 188l-18 30 20 24" stroke-width="4"/>
<path d="M30 140c20-50 50-70 90-76M300 64c40 6 70 26 90 76" stroke-dasharray="4 16"/>
<path d="M178 230l18 34-26 8z" fill="{PINK}"/><path d="M215 250l22 32-28 4z" fill="{PINK}"/><path d="M190 296l14 28-22 2z" fill="{PINK}"/>
<path d="M120 140v-18M300 140v-18"/>
<circle cx="362" cy="90" r="30" fill="{LIME}"/><path d="M350 90l10 10 18-22"/>''')

# ---- 부품
def sticker(txt_html, x, y, w, bg, rot=0, size=170, fam="inter", color=INK, z=4, cls="", pad="26px 36px 30px", sh=14, extra="", lh=".95", wt=900):
    fam_css = "'Inter','Noto Sans CJK KR'" if fam == "inter" else "'Noto Sans CJK KR','Inter'"
    return (f'<div class="blk chk {cls}" style="left:{x}px;top:{y}px;width:{w}px;background:{bg};transform:rotate({rot}deg);z-index:{z};'
            f'box-shadow:{sh}px {sh}px 0 {INK};padding:{pad};{extra}"><div class="t" style="font-family:{fam_css};font-weight:{wt};'
            f'font-size:{size}px;line-height:{lh};letter-spacing:-.02em;color:{color}">{txt_html}</div></div>')

def tag_ko(txt, x, y, rot=3, size=48, bg=INK, color=LIME, z=8):
    return (f'<div class="blk chk" style="left:{x}px;top:{y}px;background:{bg};transform:rotate({rot}deg);z-index:{z};'
            f'box-shadow:8px 8px 0 {INK};padding:10px 26px 12px;border-radius:6px;border-color:{INK}">'
            f'<div class="t" style="font-family:\'Noto Sans CJK KR\';font-weight:900;font-size:{size}px;color:{color};white-space:nowrap">{E(txt)}</div></div>')

def bubble(bid, en, ko, x, y, w, size=46, bg=PAPER, z=3):
    return (f'<div id="{bid}" class="bub chk" style="left:{x}px;top:{y}px;width:{w}px;background:{bg};z-index:{z}">'
            f'<div class="t" style="font-family:\'Inter\',\'Noto Sans CJK KR\';font-weight:800;font-size:{size}px;line-height:1.22;letter-spacing:-.01em">{E(en)}</div>'
            f'<div style="border-top:5px dotted {INK};margin:16px 0 14px"></div>'
            f'<div class="t" style="font-family:\'Noto Sans CJK KR\';font-weight:500;font-size:{int(size*.7)}px;line-height:1.38">{E(ko)}</div></div>')

def thought(txt, x, y, w, dots, rot=0, bg=LIME, size=32, z=5, rad="110px 90px 120px 80px / 90px 100px 80px 110px"):
    # dots: [(cx,cy,r)] 말풍선 기준 좌표
    d = "".join(f'<div class="blk" style="left:{cx-x-r}px;top:{cy-y-r}px;width:{2*r}px;height:{2*r}px;border-radius:50%;background:{bg};box-shadow:5px 5px 0 {INK};padding:0;border-width:5px"></div>' for cx, cy, r in dots)
    return (f'<div class="thk" style="left:{x}px;top:{y}px;width:{w}px;transform:rotate({rot}deg);z-index:{z}">{d}'
            f'<div class="blk chk" style="position:relative;background:{bg};border-radius:{rad};padding:30px 62px 32px;box-shadow:10px 10px 0 {INK}">'
            f'<div class="t" style="font-family:\'Noto Sans CJK KR\';font-weight:700;font-size:{size}px;line-height:1.38;text-align:center">{E(txt)}</div></div></div>')

def sticky(txt, x, y, w, rot=0, bg=PAPER, size=32, z=5, hole="right"):
    hx = "right:30px" if hole == "right" else "left:30px"
    return (f'<div class="stk" style="left:{x}px;top:{y}px;width:{w}px;transform:rotate({rot}deg);z-index:{z}">'
            f'<div class="stk-o"></div><div class="stk-i chk" style="background:{bg}"><div style="position:absolute;top:22px;{hx};width:20px;height:20px;border-radius:50%;background:{PAPER if bg!=PAPER else LIME};border:5px solid {INK}"></div>'
            f'<div class="t" style="font-family:\'Noto Sans CJK KR\';font-weight:700;font-size:{size}px;line-height:1.4;padding:48px 36px 28px">{E(txt)}</div></div></div>')

def tape(txt, x, y, w, rot=0, bg=PAPER, size=32, z=5, tapec=PINK):
    return (f'<div class="tp" style="left:{x}px;top:{y}px;width:{w}px;transform:rotate({rot}deg);z-index:{z}">'
            f'<div class="blk chk" style="position:relative;background:{bg};padding:22px 44px 24px;box-shadow:10px 10px 0 {INK};border-radius:4px">'
            f'<div class="t" style="font-family:\'Noto Sans CJK KR\';font-weight:700;font-size:{size}px;line-height:1.4">{E(txt)}</div></div>'
            f'<div class="strip" style="left:-30px;top:-14px;transform:rotate(-34deg);background:{tapec}"></div>'
            f'<div class="strip" style="right:-30px;bottom:-14px;transform:rotate(-34deg);background:{tapec}"></div></div>')

def ill(key, x, y, w, rot=0, z=2):
    vw, vh, body = ILL[key]; h = int(w * vh / vw)
    return f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;transform:rotate({rot}deg);z-index:{z}">{svg((vw, vh), body, w, h)}</div>'

def birdhtml(bid, x, y, h, flip=False, rot=0, plat=None, z=7):
    w = int(h * BIRD_R); out = ""
    if plat:
        px, py, pw, ph, pc = plat   # 받침: 새 기준 상대 좌표
        out += (f'<div class="blk" style="left:{x+px}px;top:{y+py}px;width:{pw}px;height:{ph}px;border-radius:50%;background:{pc};box-shadow:10px 10px 0 {INK};z-index:{z-1};padding:0"></div>')
    out += (f'<img id="{bid}" src="{BIRD}" style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{z};'
            f'transform:scaleX({-1 if flip else 1}) rotate({rot}deg)">')
    return out

def deco(kind, x, y, w, h, bg, rot=0, z=0, r=0):
    br = "50%" if kind == "circle" else f"{r}px"
    return f'<div class="blk" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{bg};border-radius:{br};transform:rotate({rot}deg);z-index:{z};padding:0;box-shadow:12px 12px 0 {INK}"></div>'

def handle(x=540, y=1264):
    return (f'<div class="chk hd" style="left:{x-290}px;top:{y}px;width:580px;z-index:20;transform:rotate(-1deg)">'
            f'<div class="t" style="font-family:\'Noto Sans CJK KR\';font-weight:700;font-size:30px;color:{PAPER};text-align:center;letter-spacing:.01em;white-space:pre">지나쌤영어  @jina.ssam_english</div></div>')

CSS = f'''
*{{box-sizing:border-box;margin:0}}
html,body{{width:1080px;height:1350px;overflow:hidden}}
body{{position:relative;font-family:'Noto Sans CJK KR','Inter',sans-serif;color:{INK}}}
#bg{{position:absolute;inset:0;overflow:hidden}}
.blk{{position:absolute;border:6px solid {INK}}}
.bub{{position:absolute;border:6px solid {INK};border-radius:30px;padding:30px 38px 32px;box-shadow:12px 12px 0 {INK}}}
.thk{{position:absolute}}
.stk{{position:absolute;filter:drop-shadow(10px 10px 0 {INK})}}
.stk-o{{position:absolute;inset:0;background:{INK};clip-path:polygon(0 0,calc(100% - 52px) 0,100% 52px,100% 100%,0 100%)}}
.stk-i{{position:relative;margin:6px;clip-path:polygon(0 0,calc(100% - 44px) 0,100% 44px,100% 100%,0 100%)}}
.tp{{position:absolute}}
.strip{{position:absolute;width:120px;height:38px;border:5px solid {INK};opacity:1;z-index:2;
 background-image:repeating-linear-gradient(90deg,transparent 0 14px,rgba(21,21,21,.0) 14px 15px)}}
.hd{{position:absolute;background:{INK};border-radius:40px;padding:12px 20px 14px}}
.t{{position:relative}}
svg{{overflow:visible}}
.t{{word-break:keep-all;overflow-wrap:break-word}}
'''

TAIL_JS = f'''
function R(e){{return e.getBoundingClientRect()}}
function tail(bid,birdid,fill){{
 var b=R(document.getElementById(bid)),g=R(document.getElementById(birdid)),W=36,sw=6,
 cx=g.left+g.width/2,cy=g.top+g.height/2,P,Q,side;
 if(g.top>=b.bottom-30)side='b';else if(g.bottom<=b.top+30)side='t';else if(g.left>=b.right-30)side='r';else side='l';
 var bx,by,tx,ty,ax,ay,px,py;
 function clamp(v,a,c){{return Math.max(a,Math.min(c,v))}}
 if(side=='b'||side=='t'){{
  bx=clamp(cx,b.left+80,b.right-80);by=side=='b'?b.bottom-3:b.top+3;
  tx=bx+(cx-bx)*.55;ty=side=='b'?g.top+g.height*.16:g.bottom-g.height*.16;
  P=[[bx-W,by],[tx,ty],[bx+W,by]];
 }}else{{
  by=clamp(cy,b.top+80,b.bottom-80);bx=side=='r'?b.right-3:b.left+3;
  ty=by+(cy-by)*.55;tx=side=='r'?g.left+g.width*.16:g.right-g.width*.16;
  P=[[bx,by-W],[tx,ty],[bx,by+W]];
 }}
 var ns='http://www.w3.org/2000/svg';
 function mk(z,inner){{var s=document.createElementNS(ns,'svg');s.setAttribute('width',1080);s.setAttribute('height',1350);
  s.style.cssText='position:absolute;left:0;top:0;z-index:'+z;s.innerHTML=inner;document.body.appendChild(s)}}
 var pts=P.map(function(p){{return p.join(',')}}).join(' ');
 var sh=P.map(function(p){{return (p[0]+12)+','+(p[1]+12)}}).join(' ');
 mk(2,'<polygon points="'+sh+'" fill="{INK}"/>');
 // 채움은 말풍선 안쪽으로 6px 넣어 외곽선을 덮는다
 var q=P.map(function(p,i){{ if(i==1)return p; var d=[0,0]; if(side=='b')d=[0,-6]; if(side=='t')d=[0,6]; if(side=='r')d=[-6,0]; if(side=='l')d=[6,0]; return [p[0]+d[0],p[1]+d[1]];}});
 var line=P.map(function(p){{return p.join(',')}}).join(' ');
 var fp=q.map(function(p){{return p.join(',')}}).join(' ');
 mk(6,'<polygon points="'+fp+'" fill="'+fill+'"/><polyline points="'+line+'" fill="none" stroke="{INK}" stroke-width="6" stroke-linejoin="miter" stroke-miterlimit="8"/>');
 window.__tails=(window.__tails||[]);window.__tails.push({{bid:bid,side:side,tip:[Math.round(tx),Math.round(ty)],base:[Math.round(bx),Math.round(by)]}});
}}
'''
CHECK_JS = '''
function check(){var out=[];
 document.querySelectorAll('.t').forEach(function(e){var r=document.createRange();r.selectNodeContents(e);var rr=r.getBoundingClientRect();
  var ox=e.scrollWidth>e.clientWidth+1;
  out.push({txt:e.textContent.slice(0,18),l:Math.round(rr.left),r:Math.round(rr.right),t:Math.round(rr.top),b:Math.round(rr.bottom),ovf:ox});});
 var d=document.createElement('pre');d.id='rep';var comps=[];document.querySelectorAll('.bub,.blk.chk,.stk,.tp,img,.thk').forEach(function(e){var q=e.getBoundingClientRect();comps.push([e.className.split(' ')[0]+':'+(e.textContent||'').slice(0,6),Math.round(q.left),Math.round(q.top),Math.round(q.right),Math.round(q.bottom)])});d.textContent=JSON.stringify({texts:out,tails:window.__tails||[],comps:comps});d.style.display='none';document.body.appendChild(d);}
'''

def page(bg, body, tails=()):
    tj = "".join(f"tail('{b}','{g}','{f}');" for b, g, f in tails)
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body style="background:{bg}"><div id="bg"></div>{body}{handle()}<script>{TAIL_JS}{CHECK_JS}'
            f'window.addEventListener("load",function(){{{tj}check();}});</script></body></html>')

# ---- 슬라이드 구성
def cover():
    c = copy["cover"]
    t = c["title"]; assert t == "AI 부정행위, 영어로는 뭐라고 할까?"
    b = ""
    b += deco("circle", 700, 640, 420, 420, PINK, z=0)
    b += sticker("AI 부정행위,", 62, 90, 840, PINK, rot=-2.5, size=124, fam="ko", wt=900, pad="18px 36px 26px", lh="1.1", sh=16, cls="ttl")
    b += sticker("영어로는", 150, 290, 700, PAPER, rot=2, size=124, fam="ko", wt=900, pad="18px 36px 26px", lh="1.1", sh=16, cls="ttl")
    b += sticker("뭐라고 할까?", 90, 490, 880, INK, rot=-1.5, size=124, fam="ko", wt=900, pad="18px 36px 26px", lh="1.1", sh=16, color=LIME, cls="ttl")
    b += tag_ko(c["sub"], 330, 730, rot=2.5, size=40, bg=PAPER, color=INK)
    b += ill("cover", 62, 840, 560, rot=-2)
    b += birdhtml("bird", 690, 880, 330, flip=True, rot=4, plat=(-30, 230, 400, 120, PAPER))
    return LIME, b, []

def c1(d):
    b = ""
    b += deco("rect", 560, 520, 600, 700, LIME, rot=8, z=0)
    b += sticker("cheat on<br>an exam", 62, 70, 900, PINK, rot=-3, size=160, pad="26px 40px 34px")
    b += tag_ko(d["ko"], 440, 410, rot=3, size=48)
    b += ill(1, 62, 560, 400, rot=-3)
    b += bubble("bub", d["en"], d["ko_ex"], 500, 570, 518, size=44)
    b += birdhtml("bird", 745, 945, 270, rot=3, plat=(-30, 205, 320, 85, PINK))
    b += thought(d["tip"], 62, 905, 580, [(676, 1060, 18), (712, 1092, 11)], rot=-2, size=30)
    b += tape(d["link"], 90, 1140, 640, rot=-1.5, size=28)
    return PAPER, b, [("bub", "bird", PAPER)]

def c2(d):
    b = ""
    b += deco("circle", -180, 760, 560, 560, LIME, z=0)
    b += birdhtml("bird", 62, 80, 280, flip=True, rot=-4, plat=(-10, 215, 300, 80, LIME))
    b += bubble("bub", d["en"], d["ko_ex"], 410, 80, 608, size=46)
    b += sticker("detect", 190, 470, 790, LIME, rot=2.5, size=200, pad="22px 44px 34px")
    b += tag_ko(d["ko"], 100, 705, rot=-3, size=48)
    b += ill(2, 640, 800, 380, rot=3)
    b += sticky(d["tip"], 62, 830, 500, rot=-2.5, bg=PAPER, size=30)
    b += tape(d["link"], 100, 1125, 600, rot=1.5, size=28, bg=LIME, tapec=PINK)
    return PINK, b, [("bub", "bird", PAPER)]

def c3(d):
    b = ""
    b += deco("rect", 30, 300, 420, 760, PINK, rot=-6, z=0)
    b += sticker("blind<br>spot", 380, 70, 600, LIME, rot=2, size=190, pad="22px 44px 34px")
    b += tag_ko(d["ko"], 80, 205, rot=-4, size=46)
    b += ill(3, 62, 350, 400, rot=-2, z=3)
    b += birdhtml("bird", 90, 870, 270, rot=-3, plat=(-20, 205, 310, 80, LIME))
    b += bubble("bub", d["en"], d["ko_ex"], 490, 548, 528, size=46)
    b += tape(d["tip"], 430, 945, 588, rot=2, size=28, bg=PAPER, tapec=LIME)
    b += sticky(d["link"], 410, 1105, 608, rot=-1.5, bg=LIME, size=28, hole="left")
    return PAPER, b, [("bub", "bird", PAPER)]

def c4(d):
    b = ""
    b += deco("circle", 600, 40, 520, 520, PINK, z=0)
    b += sticker("crack<br>down on", 62, 60, 820, PAPER, rot=-2, size=160, pad="26px 40px 34px")
    b += tag_ko(d["ko"], 520, 400, rot=3, size=48)
    b += birdhtml("bird", 730, 530, 260, flip=True, rot=5, plat=(-20, 185, 300, 80, PINK))
    b += bubble("bub", d["en"], d["ko_ex"], 62, 500, 560, size=44)
    b += ill(4, 610, 830, 400, rot=4)
    b += thought(d["tip"], 62, 880, 520, [(560, 1060, 18), (600, 1092, 11)], rot=2, bg=LIME, size=29)
    b += sticky(d["link"], 80, 1095, 640, rot=-1.5, bg=PAPER, size=28)
    return LIME, b, [("bub", "bird", PAPER)]

def c5(d):
    b = ""
    b += deco("rect", 560, 330, 520, 800, LIME, rot=-7, z=0)
    b += birdhtml("bird", 120, 70, 300, rot=-3, plat=(-20, 230, 340, 90, LIME))
    b += bubble("bub", d["en"], d["ko_ex"], 440, 70, 578, size=44)
    b += sticker("erode<br>trust", 62, 470, 820, PINK, rot=-2.5, size=170, pad="22px 44px 34px")
    b += tag_ko(d["ko"], 520, 830, rot=-3, size=48)
    b += ill(5, 620, 930, 380, rot=-2, z=3)
    b += sticky(d["tip"], 62, 900, 520, rot=2, bg=PAPER, size=28)
    b += tape(d["link"], 90, 1135, 520, rot=-1.5, size=28, bg=LIME, tapec=PINK)
    return PAPER, b, [("bub", "bird", PAPER)]

SLIDES = [("slide_00_cover", cover, None)] + [(f"slide_{i+1:02d}", f, i) for i, f in enumerate([c1, c2, c3, c4, c5])]

def chrome(args):
    return subprocess.run(["google-chrome", "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                           "--force-device-scale-factor=2", "--window-size=1080,1350"] + args, capture_output=True, text=True, timeout=120)

report = {}
for name, fn, idx in SLIDES:
    bg, body, tails = fn() if idx is None else fn(copy["cards"][idx])
    path = f"{OUT}/{name}.html"
    open(path, "w").write(page(bg, body, tails))
    dom = chrome(["--virtual-time-budget=3000", "--dump-dom", f"file://{path}"]).stdout
    m = re.search(r'<pre id="rep"[^>]*>(.*?)</pre>', dom, re.S)
    report[name] = json.loads(html.unescape(m.group(1))) if m else None
    tmp = tempfile.mktemp(suffix=".png")
    chrome([f"--screenshot={tmp}", f"file://{path}"])
    im = Image.open(tmp).convert("RGB")
    im.save(f"{OUT}/{name}_2x.png") if os.environ.get("KEEP2X") else None
    im.resize((1080, 1350), Image.LANCZOS).save(f"{OUT}/{name}.png"); os.remove(tmp)

# 안전 여백 점검
bad = []
for n, r in report.items():
    for t in r["texts"]:
        if t["l"] < 62 or t["r"] > 1018 or t["ovf"]:
            bad.append((n, t))
json.dump({"contrast": contrast, "bad": bad, "comps": {n: r["comps"] for n, r in report.items()} if os.environ.get("COMPS") else None, "tails": {n: r["tails"] for n, r in report.items()}}, sys.stdout, ensure_ascii=False, indent=1)

# 컨택트 시트
W, H, g = 360, 450, 16
sheet = Image.new("RGB", (W * 3 + g * 4, H * 2 + g * 3), (30, 30, 30))
for i, (name, _, _) in enumerate(SLIDES):
    im = Image.open(f"{OUT}/{name}.png").resize((W, H), Image.LANCZOS)
    sheet.paste(im, (g + (i % 3) * (W + g), g + (i // 3) * (H + g)))
sheet.save(f"{OUT}/contact_sheet.png")
