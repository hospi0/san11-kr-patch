import struct, sys
import numpy as np
from PIL import Image, ImageDraw
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
def get(i):
    a,b=tbl[i]; f.seek(a*0x800); return f.read(b)
d=get(1)
print("idx1 size",len(d))
print("head:",d[:0x40].hex())
marker,count=struct.unpack("<II",d[:8])
print("marker %x count %d"%(marker,count))
# after 0000feff + count + name(16?) find sub-table. Dump u32s from 0x08..0x60
print("u32 dump 0x00..0x80:")
for o in range(0,0x80,16):
    print(f"  0x{o:02x}: "+" ".join(f"{x:08x}" for x in struct.unpack('<4I',d[o:o+16])))
# The name "KOEI%SAN11" at 0x08. count=8. Table maybe at 0x20: pairs (off,size)?
# Let's scan for plausible offset table: increasing u32 < len
cands=[]
for base in [0x18,0x1c,0x20,0x28,0x30]:
    vals=struct.unpack("<%dI"%count, d[base:base+4*count])
    if all(0<=v<len(d) for v in vals) and list(vals)==sorted(vals):
        cands.append((base,vals))
print("offset-table candidates:",[(hex(b),[hex(x) for x in v]) for b,v in cands])
