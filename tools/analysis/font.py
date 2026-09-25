import struct, io, sys
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10)
tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]

def get(i):
    a,b=tbl[i]; f.seek(a*0x800); return f.read(b)

d=get(1)
print("idx1 size",len(d),"head hex:",d[:32].hex())

def render_1bpp(data, base, W, H, count, cols=16):
    rowbytes=(W+7)//8
    glyph=rowbytes*H
    lines=[""]*(H*((count+cols-1)//cols))
    out=[]
    for g in range(count):
        gd=data[base+g*glyph: base+(g+1)*glyph]
        for y in range(H):
            row=""
            for x in range(W):
                byte=gd[y*rowbytes + x//8] if y*rowbytes+x//8<len(gd) else 0
                bit=(byte>>(7-(x%8)))&1
                row+="█" if bit else "·"
            out.append(row)
        out.append("")
    return out

for (W,H) in [(12,12),(16,16),(24,24)]:
    with io.open(f"{OUT}/font_{W}x{H}.txt","w",encoding="utf-8") as w:
        # try a few base offsets
        for base in [0x20,0x30,0x80,0x100,0x200]:
            w.write(f"\n##### base=0x{base:x} {W}x{H} #####\n")
            for line in render_1bpp(d, base, W, H, 6):
                w.write(line+"\n")
    print(f"wrote font_{W}x{H}.txt")
