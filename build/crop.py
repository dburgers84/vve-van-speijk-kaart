"""Uitsnede van de referentiescan met rooster in tekeningeenheden. Gebruik: python3 build/crop.py 1e x0 y0 x1 y1 [zoom] [uit.png]"""
import sys
from PIL import Image, ImageDraw
f,x0,y0,x1,y1=sys.argv[1],*map(float,sys.argv[2:6]); z=float(sys.argv[6]) if len(sys.argv)>6 else 4
import os
im=Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','img',f'plan_{f}.jpg')).convert('RGB')
P=lambda x,y:((x-30)*1.5,y*1.5)
a=P(x0,y0);b=P(x1,y1)
r=im.crop((int(a[0]),int(a[1]),int(b[0]),int(b[1])))
k=z/1.5
r=r.resize((int(r.width*k),int(r.height*k)))
d=ImageDraw.Draw(r)
import math
step=10
for gx in range(int(math.ceil(x0/step)*step),int(x1)+1,step):
  X=(gx-x0)*z; d.line([(X,0),(X,r.height)],fill=(255,0,0) if gx%50==0 else (255,180,180),width=1)
  if gx%20==0: d.text((X+2,2),str(gx),fill=(200,0,0))
for gy in range(int(math.ceil(y0/step)*step),int(y1)+1,step):
  Y=(gy-y0)*z; d.line([(0,Y),(r.width,Y)],fill=(0,0,255) if gy%50==0 else (180,180,255),width=1)
  if gy%20==0: d.text((2,Y+2),str(gy),fill=(0,0,200))
out=sys.argv[7] if len(sys.argv)>7 else f'/tmp/crop_{f}_{int(x0)}_{int(y0)}.png'
r.save(out);print(out,r.size)
