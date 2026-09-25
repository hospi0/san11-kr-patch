import struct, sys, bisect
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
secstarts=[a*0x800 for a,b in tbl]
def which(off):
    i=bisect.bisect_right(secstarts,off)-1
    a,b=tbl[i]; s=a*0x800
    return (i, off-s, b) if off<s+b else (None,None,None)
for off in [0x5bcaf70, 0x5546298, 0x5a707e2]:
    i,rel,sz=which(off)
    print(f"off {off:#x} -> entry idx={i} rel={rel:#x} entry_size={sz}")
    if i is not None:
        a,b=tbl[i]; f.seek(a*0x800); h=f.read(48)
        print("   entry head:", h.hex())
        f.seek(off-16); ctx=f.read(96)
        print("   context:", ctx.hex())
