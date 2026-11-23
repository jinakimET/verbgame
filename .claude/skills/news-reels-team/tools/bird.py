import numpy as np, subprocess
from PIL import Image, ImageDraw, ImageFilter
SPR='/home/user/verbgame/content/assets/bird_sprite.png'
src=Image.open(SPR).convert('RGBA'); A0=np.array(src).astype(np.int16)
R,G,B,AL=A0[...,0],A0[...,1],A0[...,2],A0[...,3]
core=np.zeros(R.shape,bool)
core[80:141,130:236]=((R>170)&(R-G>40)&(R-B>50)&(AL>128))[80:141,130:236]
ys,xs=np.nonzero(core)
# full beak extent: warm (non-green) pixels connected around the core, inside a box padded from core bbox
x0,x1,y0,y1=xs.min()-8,xs.max()+8,ys.min()-12,ys.max()+8
warm=np.zeros_like(core); warm[y0:y1+1,x0:x1+1]=((R-G>12)&(AL>128))[y0:y1+1,x0:x1+1]
bm=Image.fromarray((warm*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
beak=np.array(bm)>0
bys,bxs=np.nonzero(beak); BX0,BX1,BY0,BY1=bxs.min(),bxs.max(),bys.min(),bys.max()
MID=int(round(np.median(ys)))
# fur fill colour: fur directly above and beside the beak
ring=np.zeros_like(beak); ring[BY0-14:BY0-3,BX0:BX1+1]=True; ring[BY0:BY1+1,BX0-16:BX0-4]=True; ring[BY0:BY1+1,BX1+4:BX1+16]=True
ring&=(AL>200)&(G>R)
FUR=np.median(A0[ring][:,:3],0).astype(np.uint8)
print('beak bbox',BX0,BX1,BY0,BY1,'MID',MID,'fur',FUR)
# beak pieces: undilated warm mask, feathered edge
pm=np.array(Image.fromarray((warm*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)/255
beak_rgba=np.array(src).copy(); beak_rgba[...,3]=(beak_rgba[...,3]*pm).astype(np.uint8)
upper=beak_rgba.copy(); upper[MID:,:,3]=0
lower=beak_rgba.copy(); lower[:MID,:,3]=0
# fill the (dilated) beak area by diffusing surrounding fur inward
f=np.array(src)[...,:3].astype(np.float32); f[beak]=FUR
yy0,yy1,xx0,xx1=BY0-6,BY1+40,BX0-6,BX1+7
reg=f[yy0:yy1,xx0:xx1]; mk=beak[yy0:yy1,xx0:xx1]
for _ in range(400):
    av=(np.roll(reg,1,0)+np.roll(reg,-1,0)+np.roll(reg,1,1)+np.roll(reg,-1,1))/4
    reg[mk]=av[mk]
rng=np.random.default_rng(1); reg[mk]+=rng.normal(0,5,(mk.sum(),1))
f[yy0:yy1,xx0:xx1]=reg
fimg=Image.fromarray(np.clip(f,0,255).astype(np.uint8)); fimg.putalpha(src.getchannel('A'))
UP=Image.fromarray(upper); LO=Image.fromarray(lower)
H_OUT=240
def mouth(a):
    op=12*a
    im=fimg.copy()
    if a>0.02:
        d=ImageDraw.Draw(im); cx=(BX0+BX1)/2; w=(BX1-BX0)*0.62; h=op+6
        d.ellipse((cx-w/2,MID-2,cx+w/2,MID-2+h),fill=(70,25,30,255))
    im.alpha_composite(UP)
    im.alpha_composite(LO,(0,int(round(op))))
    return im
_cache={}
def sprite(a):
    q=round(a*16)/16
    if q in _cache: return _cache[q]
    im=mouth(q); s=H_OUT/im.height
    sx,sy=1+0.015*q,1-0.025*q
    w,h=int(round(im.width*s*sx)),int(round(H_OUT*sy))
    _cache[q]=im.resize((w,h),Image.LANCZOS); return _cache[q]
def place(fr,a,cx=720,bottom=566):
    sp=sprite(a); fr.alpha_composite(sp,(int(round(cx-sp.width/2)),bottom-sp.height))
def envelope(mp3,fps=30,n=None):
    raw=subprocess.run(['ffmpeg','-loglevel','error','-i',mp3,'-ac','1','-ar','8000','-f','s16le','-'],capture_output=True).stdout
    x=np.frombuffer(raw,np.int16).astype(np.float32)/32768; hop=8000//fps
    m=len(x)//hop; rms=np.sqrt((x[:m*hop].reshape(m,hop)**2).mean(1))
    v=np.clip(rms/np.percentile(rms,90),0,1)**0.8
    out=np.zeros(m); cur=0
    for i,val in enumerate(v):
        cur=val if val>cur else cur*0.6
        out[i]=cur
    if n and len(out)<n: out=np.pad(out,(0,n-len(out)))
    return out
if __name__=='__main__':
    bgc=Image.new('RGBA',(560,300),(60,50,140,255))
    c=mouth(0); o=mouth(1.0)
    crop=(BX0-40,BY0-40,BX1+40,BY1+50)
    for i,im in enumerate([c,o]):
        t=Image.new('RGBA',im.size,(60,50,140,255)); t.alpha_composite(im)
        z=t.crop(crop); z=z.resize((z.width*2,z.height*2),Image.LANCZOS)
        full=t.resize((int(t.width*0.6),int(t.height*0.6)))
        if i==0: canvas=Image.new('RGB',(2*max(z.width,full.width)+30,z.height+full.height+30),(30,30,60))
        canvas.paste(full.convert('RGB'),(i*(canvas.width//2)+10,10)); canvas.paste(z.convert('RGB'),(i*(canvas.width//2)+10,full.height+20))
    __import__('os').makedirs(__import__('os').environ.get('NEWS_ROOT','.')+'/06_keyword_reels/frames',exist_ok=True); canvas.save(__import__('os').environ.get('NEWS_ROOT','.')+'/06_keyword_reels/frames/check_mouth.png')
