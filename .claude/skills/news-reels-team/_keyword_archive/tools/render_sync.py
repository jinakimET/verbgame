import json, re, subprocess, sys, numpy as np
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import bird
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H,FPS=1080,1920,30
ROOT=__import__("os").environ.get("NEWS_ROOT","/home/user/verbgame/content/2026-11-23-cnn").rstrip("/")+"/"
OUT=ROOT+'04_sync_reel/'
scenes=json.load(open(ROOT+'03_script/sync_scenes.json'))['scenes']
words={w['id']:w for w in json.load(open(ROOT+'audio/words.json'))}
KR='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
EN='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
ENB='/usr/share/fonts/opentype/inter/Inter-Bold.otf'
def kr(s): return ImageFont.truetype(KR,s,index=1)
def norm(t): return re.sub(r"[^a-z0-9']","",t.lower().replace('(2)','').replace('(3)',''))
def toks(t): return [x for x in t.split()]

# ---------- timing ----------
plan=[]
for sc in scenes:
    it=words[sc['expr_id']]
    ew=[(norm(re.sub(r'\(\d\)','',w)),s,e) for w,s,e in it['eng_words']]
    segs=it['segments']
    term=[norm(x) for x in toks(sc['term']) if norm(x)]
    assert [w[0] for w in ew[:len(term)]]==term,(sc['scene'],ew[:len(term)],term)
    t_term=ew[0][1]
    rest=ew[len(term):]
    ex=[l for l in sc['lines'] if l['role']=='example_en'][0]
    et=toks(ex['text']); en=[norm(x) for x in et]
    times=[None]*len(et); j=0
    for i,w in enumerate(en):
        if j<len(rest) and rest[j][0]==w: times[i]=rest[j][1]; j+=1
    assert j==len(rest),(sc['scene'],en,rest)
    # snap early first word: only when the 1st example word sits in segment 1 but the 2nd is already past it
    if len(segs)>1 and times[0]<segs[0][1] and times[1] is not None and times[1]>=segs[0][1]:
        nxt=[s for s,e in segs if s>times[0]][0]; times[0]=nxt
    if times[0] is None: raise SystemExit('no first word time')
    sp=ex.get('split_at')
    t_l2=times[sp] if sp else None
    hl=ex['highlight'].split(); hn=[norm(x) for x in hl]
    hi=[i for i in range(len(en)) if en[i:i+len(hn)]==hn][0]
    t_hl=times[hi]
    plan.append(dict(sc=sc,t_term=t_term,t_ex=times[0],t_l2=t_l2,hi=hi,hn=len(hn),t_hl=t_hl,t_ko=it['kor'][0],
                     end_speech=max(it['kor'][1],segs[-1][1])))
for i,p in enumerate(plan):
    p['start']=max(0.0,p['t_term']-0.3)
for i,p in enumerate(plan):
    p['end']=plan[i+1]['start'] if i+1<len(plan) else p['end_speech']+0.5
TOTAL=plan[-1]['end']
for p in plan:
    print(p['sc']['scene'],'start %.2f term %.2f ex %.2f l2 %s hl %.2f ko %.2f end %.2f'%(p['start'],p['t_term'],p['t_ex'],None if p['t_l2'] is None else round(p['t_l2'],2),p['t_hl'],p['t_ko'],p['end']))
print('TOTAL',TOTAL)
json.dump([{k:v for k,v in p.items() if k!='sc'}|{'scene':p['sc']['scene']} for p in plan],open(OUT+'timing.json','w'),indent=1)
if '--dry' in sys.argv: sys.exit()

# ---------- base ----------
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
def blob(cx,cy,r): return np.exp(-(((xx-cx)**2+(yy-cy)**2)/(2*r*r)))[...,None]
g=(yy/H)[...,None]
bg=np.array([18,16,52])*(1-g)+np.array([10,14,36])*g
bg=bg+blob(200,420,380)*np.array([110,50,200])+blob(900,1300,420)*np.array([40,60,170])+blob(560,1750,360)*np.array([90,40,150])*0.8+blob(980,250,260)*np.array([60,30,140])
BG=Image.fromarray(np.clip(bg,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40))
PX0,PY0,PX1,PY1,R=70,560,1010,1230,56
glass=BG.filter(ImageFilter.GaussianBlur(26))
glass=Image.blend(glass,Image.new('RGB',(W,H),(255,255,255)),0.10)
m=Image.new('L',(W,H),0); ImageDraw.Draw(m).rounded_rectangle((PX0,PY0,PX1,PY1),R,fill=255)
base=BG.copy(); base.paste(glass,(0,0),m); base=base.convert('RGBA')
ov=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
d.rounded_rectangle((PX0,PY0,PX1,PY1),R,outline=(255,255,255,110),width=3)
d.rounded_rectangle((PX0+5,PY0+5,PX1-5,PY1-5),R-5,outline=(255,255,255,36),width=2)
# pill
pf=ImageFont.truetype(ENB,32); pt='NEWS ENGLISH · CNN'
tw=d.textlength(pt,font=pf); pw=tw+64
d.rounded_rectangle(((W-pw)/2,220,(W+pw)/2,286),33,fill=(139,61,255,255))
d.text((W/2,253),pt,font=pf,fill=(255,255,255,255),anchor='mm')
# handle
d.text((W/2,1588),'지나쌤영어  @jina.ssam_english',font=kr(30),fill=(255,255,255,235),anchor='ma')
base=Image.alpha_composite(base,ov)

# ---------- layers ----------
MAXW=820
def fit(fontf,text,size,maxw=MAXW,minsize=30):
    while size>minsize:
        f=fontf(size)
        if f.getlength(text)<=maxw: return f
        size-=2
    return fontf(size)
def mklayer(draw_fn):
    L=Image.new('RGBA',(W,H),(0,0,0,0)); draw_fn(ImageDraw.Draw(L)); bb=L.getbbox()
    return (L.crop(bb),bb[:2]) if bb else None
WHITE=(255,255,255,255); BOXC=(210,189,255,255); DARK=(23,25,27,255)
def en_font(s): return ImageFont.truetype(EN,s)
def build(p):
    sc=p['sc']; lay=[]
    term=sc['term']
    ft=fit(en_font,term,96)
    lay.append(dict(t=p['t_term'],img=mklayer(lambda d:d.text((W/2,770),term,font=ft,fill=WHITE,anchor='ms'))))
    ex=[l for l in sc['lines'] if l['role']=='example_en'][0]; et=ex['text'].split(); sp=ex.get('split_at')
    rows=[(et[:sp],p['t_ex'],0),(et[sp:],p['t_l2'],sp)] if sp else [(et,p['t_ex'],0)]
    size=64
    for r,_,_ in rows: size=min(size,fit(en_font,' '.join(r),64).size)
    fe=en_font(size)
    ys=[905,990] if sp else [945]
    GAP=12
    def segs_of(r,off):
        hs,he=p['hi'],p['hi']+p['hn']
        if not (off<=hs<off+len(r)): return [(' '.join(r),False)]
        pre=' '.join(r[:hs-off]); mid=' '.join(r[hs-off:he-off]); post=' '.join(r[he-off:])
        tail=''
        m=re.search(r'[.,!?]+$',mid)
        if m: tail=m.group(0); mid=mid[:m.start()]
        out=[]
        if pre: out.append((pre+' ','gap'))
        out.append((mid,True))
        rest=(tail+(' ' if post else '')+post) if tail else (' '+post if post else '')
        if rest: out.append(('gap2',None)); out.append((rest,False))
        return out
    for (r,t,off),y in zip(rows,ys):
        sg=segs_of(r,off)
        def wid(seg):
            txt,k=seg
            if txt=='gap2': return GAP
            return fe.getlength(txt)+(GAP if k=='gap' else 0)
        tot=sum(wid(x) for x in sg); x=W/2-tot/2; pos=[]
        for seg in sg:
            pos.append(x); x+=wid(seg)
        def dline(d,sg=sg,pos=pos,y=y):
            for (txt,k),px in zip(sg,pos):
                if txt!='gap2': d.text((px,y),txt,font=fe,fill=WHITE,anchor='ls')
        lay.append(dict(t=t,img=mklayer(dline)))
        for (txt,k),px in zip(sg,pos):
            if k is True:
                hwid=fe.getlength(txt)
                def dbox(d,hx=px,hw=txt,hwid=hwid,y=y):
                    d.rounded_rectangle((hx-14,y-size*0.80,hx+hwid+14,y+size*0.26),14,fill=BOXC)
                    d.text((hx,y),hw,font=fe,fill=DARK,anchor='ls')
                lay.append(dict(t=p['t_hl'],img=mklayer(dbox),box=True))
                assert px-14>=PX0+30 and px+hwid+14<=PX1-30,(sc['scene'],px,hwid)
    ko=[l for l in sc['lines'] if l['role']=='example_ko'][0]['text']
    fk=fit(kr,ko,52)
    lay.append(dict(t=p['t_ko'],img=mklayer(lambda d:d.text((W/2,1110),ko,font=fk,fill=(235,228,255,255),anchor='ms'))))
    # bounds check
    for l in lay:
        im,(x,y)=l['img']; assert PX0<x and x+im.width<PX1 and PY0<y and y+im.height<PY1,(sc['scene'],x,y,im.size)
    return lay
for p in plan: p['layers']=build(p)

FADE=0.35; SLIDE=50
def ease(u): return 1-(1-u)**3
def scene_frame(now):
    p=[q for q in plan if q['start']<=now<q['end']]
    fr=base.copy()
    if not p: return fr
    for l in p[0]['layers']:
        dt=now-l['t']
        if dt<0: continue
        im,(x,y)=l['img']
        if l.get('box'):
            u=min(1,dt/0.2); dy=0
        else:
            u=min(1,dt/FADE); dy=int(round(SLIDE*(1-ease(u))))
        if u<1:
            a=im.getchannel('A').point(lambda v,k=ease(u):int(v*k)); im=im.copy(); im.putalpha(a)
        fr.alpha_composite(im,(x,y+dy))
    return fr

ENV=None
def frame_for(now,fr=None):
    global ENV
    if ENV is None: ENV=bird.envelope(ROOT+'audio/voice_full.mp3',FPS,int(TOTAL*FPS)+5)
    fr=(fr if fr is not None else scene_frame(now)).copy()
    i=int(round(now*FPS)); bird.place(fr,float(ENV[i]) if i<len(ENV) else 0.0)
    return fr
if '--check' in sys.argv:
    for name,t in [(a.split('=')[0],float(a.split('=')[1])) for a in sys.argv if '=' in a]:
        frame_for(t).convert('RGB').save(OUT+f'frames/check_{name}.png')
    sys.exit()
N=int(round(TOTAL*FPS))
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
    '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-threads','2',OUT+'silent.mp4'],stdin=subprocess.PIPE)
cache={}
for i in range(N):
    now=i/FPS
    # cache static frames by state key
    p=[q for q in plan if q['start']<=now<q['end']]
    key=None
    if p:
        st=tuple(min(1.0,max(-1,now-l['t'])) if now-l['t']<0.36 else 9 for l in p[0]['layers'])
        if all(s<0 or s==9 for s in st): key=(p[0]['sc']['scene'],tuple(s==9 for s in st))
    if key and key in cache: sf=cache[key]
    else:
        sf=scene_frame(now)
        if key: cache={key:sf}
    ff.stdin.write(frame_for(now,sf).convert('RGB').tobytes())
ff.stdin.close(); ff.wait()
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',OUT+'silent.mp4','-i',ROOT+'audio/voice_full.mp3','-map','0:v','-map','1:a',
    '-c:v','copy','-c:a','aac','-b:a','192k','-af','apad','-t',f'{TOTAL:.3f}',OUT+'reel_sync.mp4'],check=True)
print('done',N)
