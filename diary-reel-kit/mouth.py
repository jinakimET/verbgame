import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import cv2, numpy as np
from PIL import Image
CH = np.array(Image.open(_HERE + "/char.png"))
# mouth center (lip seam) and region in char coords
MX, MY = 335, 568
X0,Y0,X1,Y1 = 230, 470, 440, 700
sub = CH[Y0:Y1, X0:X1].astype(np.float32)
hh, ww = sub.shape[:2]
yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
cx, cy = MX-X0, MY-Y0
# weight: strong on lower lip/jaw below seam, falls off sideways and downward
gx = np.exp(-((xx-cx)/62.0)**2)
below = np.clip((yy-cy+6)/18.0, 0, 1)            # ramps in just above seam
fall = np.exp(-np.clip(yy-cy-30,0,None)/55.0)       # fades toward chin/neck
W = gx*below*fall
def warp(open_amt):
    """open_amt in px: + opens jaw, - closes"""
    dy = W*open_amt
    mx = xx; my = yy - dy
    out = cv2.remap(sub, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    res = CH.copy(); res[Y0:Y1, X0:X1] = out.astype(np.uint8)
    return res
if __name__=='__main__':
    tiles=[Image.fromarray(warp(a)).crop((200,430,470,720)) for a in (-14,-6,0,8)]
    W2=sum(t.width for t in tiles); s=Image.new('RGBA',(W2,tiles[0].height),(40,90,60,255))
    x=0
    for t in tiles: s.alpha_composite(t,(x,0)); x+=t.width
    s.convert('RGB').resize((W2*2,tiles[0].height*2)).save(_HERE + "/mouth_test.jpg")
