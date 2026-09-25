import struct, sys
import numpy as np
from PIL import Image
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
def get(i):
    a,b=tbl[i]; f.seek(a*0x800); return f.read(b)
d=get(675)
print("size",len(d))
body=d[16:]  # skip GCOL0002
a=np.frombuffer(body,np.uint8)
for w in [256,320,384,512,640,720]:
    h=len(a)//w
    img=Image.fromarray(a[:w*h].reshape(h,w),"L")
    img.save(f"{OUT}/gcol675_8bpp_w{w}.png")
print("saved 8bpp variants; body bytes hist top:")
vals,cnts=np.unique(a,return_counts=True)
order=np.argsort(-cnts)[:8]
print([(int(vals[o]),int(cnts[o])) for o in order])
