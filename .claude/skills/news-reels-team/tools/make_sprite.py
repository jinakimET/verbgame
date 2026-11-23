from PIL import Image, ImageFilter
import numpy as np
from collections import deque
im=Image.open('/root/.claude/uploads/76f86c00-49e8-5ad5-9004-56c0f347232b/59156617-image.jpg').convert('RGB')
a=np.asarray(im).astype(int); H,W,_=a.shape
print(W,H)
corners=np.array([a[5,5],a[5,W-6],a[H-6,5],a[H-6,W-6]]); bg=np.median(corners,0); print('bg',bg)
dist=np.sqrt(((a-bg)**2).sum(2))
mask=np.zeros((H,W),bool); q=deque()
for x in range(W): q.append((0,x)); q.append((H-1,x))
for y in range(H): q.append((y,0)); q.append((y,W-1))
TH=30
while q:
    y,x=q.popleft()
    if mask[y,x] or dist[y,x]>=TH: continue
    mask[y,x]=True
    if y>0: q.append((y-1,x))
    if y<H-1: q.append((y+1,x))
    if x>0: q.append((y,x-1))
    if x<W-1: q.append((y,x+1))
fg=~mask
ys,xs=np.where(fg); print('bbox',xs.min(),xs.max(),ys.min(),ys.max())
np.save('fg.npy',fg)
alpha=Image.fromarray((fg*255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.0))
rgba=im.copy(); rgba.putalpha(alpha)
rgba.save('bird_full.png')
