import struct, sys
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
def get(i):
    a,b=tbl[i]; f.seek(a*0x800); return f.read(b)
d=get(88)[0x40:0x40+200000]
# byte-level autocorrelation to find row stride (popcount diff)
import numpy as np
a=np.frombuffer(d,dtype=np.uint8).astype(np.int32)
best=[]
for stride in range(8, 200):
    x=a[:-stride]; y=a[stride:]
    score=np.mean(x==y)  # fraction equal
    best.append((score,stride))
best.sort(reverse=True)
print("idx88 top strides (byte-equal fraction):")
for s,st in best[:12]: print(f"  stride={st:4} score={s:.3f}")

# FCVD check
d2=get(1023)
print("\nidx1023 FCVD head:", d2[:32].hex())
