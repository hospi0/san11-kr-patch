import struct, io, sys, re
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10)
tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
def get(i):
    a,b=tbl[i]; f.seek(a*0x800); return f.read(b)
with io.open(OUT+"/rec.txt","w",encoding="utf-8") as w:
    for idx in [90, 91, 92, 2517, 1015]:
        d=get(idx)
        w.write(f"\n===== idx={idx} size={len(d)} head={d[:16].hex()} =====\n")
        # any short coherent JP substrings (2-8 chars, name-like)
        found=[]
        for m in re.finditer(rb'(?:[\x88-\x9f\xe0-\xea][\x40-\xfc]){2,8}', d):
            try:
                s=m.group().decode('cp932')
                found.append(s)
            except: pass
        w.write(f" jp-substrings sample ({len(found)} total): "+" | ".join(found[:40])+"\n")
print("done")
