import cv2, numpy as np, json, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
def boxsum(I,x0,y0,x1,y1):  # arrays of coords, inclusive-exclusive, I integral (H+1,W+1)
    return I[y1,x1]-I[y0,x1]-I[y1,x0]+I[y0,x0]
def detect(page):
    g=np.array(Image.open(f'/workspace/vve-source-audit/page-{page}.png').convert('L'))
    B=(g<170).astype(np.int32)
    B=cv2.dilate(B.astype(np.uint8),np.ones((2,2),np.uint8)).astype(np.int64)
    I=np.zeros((B.shape[0]+1,B.shape[1]+1),np.int64); I[1:,1:]=B.cumsum(0).cumsum(1)
    H,W=B.shape
    best=np.zeros((H,W),np.float32); bs=np.zeros((H,W),np.int16)
    for s in range(8,27,2):
        t=max(2,s//5)
        # we compute using slicing for efficiency
        def S(o,sz):
            return I[o+sz:H-s+o+sz, o+sz:W-s+o+sz]-I[o:H-s+o, o+sz:W-s+o+sz]-I[o+sz:H-s+o+sz, o:W-s+o]+I[o:H-s+o, o:W-s+o]
        full=S(0,s); inn=S(t,s-2*t); core=S(t+1,s-2*t-2)
        ring=(full-inn)/(s*s-(s-2*t)**2)
        # side checks: top, bottom, left, right strips
        def strip(y0,x0,h,w):
            return (I[y0+h:H-s+y0+h, x0+w:W-s+x0+w]-I[y0:H-s+y0, x0+w:W-s+x0+w]-I[y0+h:H-s+y0+h, x0:W-s+x0]+I[y0:H-s+y0, x0:W-s+x0])/(h*w)
        sides=np.minimum.reduce([strip(0,0,t,s),strip(s-t,0,t,s),strip(0,0,s,t),strip(0,s-t,s,t)])
        interior=core/max(1,(s-2*t-2)**2)
        score=np.where((interior<0.06),sides,0).astype(np.float32)
        tgt=best[s//2:s//2+H-s, s//2:s//2+W-s]
        m=score>tgt
        tgt[m]=score[m]; bs[s//2:s//2+H-s, s//2:s//2+W-s][m]=s
    ys,xs=np.where(best>=0.85)
    order=np.argsort(-best[ys,xs]); taken=np.zeros((H,W),bool); out=[]
    for i in order:
        y,x=ys[i],xs[i]
        if taken[max(0,y-14):y+14,max(0,x-14):x+14].any(): continue
        taken[y,x]=True
        s=int(bs[y,x]); m=6
        # attached if ink immediately outside the square
        o=B[max(0,y-s//2-m):y+s//2+m, max(0,x-s//2-m):x+s//2+m].sum()-B[y-s//2:y+s//2, x-s//2:x+s//2].sum()
        out.append({"x":int(x),"y":int(y),"size_px":s,"side_min":round(float(best[y,x]),2),"outside_ink_px":int(o)})
    return out
if __name__=='__main__':
    res={}
    for p in map(int,sys.argv[1:]):
        res[p]=detect(p); print(p,len(res[p]),'isolated',sum(c['outside_ink_px']<10 for c in res[p]))
    json.dump(res,open('cols3_all.json','w'))
