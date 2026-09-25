import struct, io, sys, bisect, re
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10)
tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
secstarts=[a*0x800 for a,b in tbl]
def which(off):
    i=bisect.bisect_right(secstarts,off)-1
    a,b=tbl[i]; start=a*0x800
    if off < start+b: return i, off-start
    return None, None

hits=[0x11fb85,0x1372c0,0x1f5e73,0x220000,0x2cc800]
w=io.open(OUT+"/locate.txt","w",encoding="utf-8")
seen=set()
for h in hits:
    i,rel=which(h)
    if i is None: 
        w.write(f"off {h:#x}: (in padding)\n"); continue
    if i in seen: continue
    seen.add(i)
    a,b=tbl[i]; f.seek(a*0x800); d=f.read(b)
    w.write(f"\n===== off {h:#x} -> entry idx={i} size={b} magic={d[:8].hex()} rel={rel:#x} =====\n")
    # decode a window, showing readable text with control bytes as [XX]
    win=d[max(0,rel-64):rel+220]
    out=""
    j=0
    while j<len(win):
        c=win[j]
        if (0x81<=c<=0x9f or 0xe0<=c<=0xef) and j+1<len(win):
            try:
                out+=win[j:j+2].decode("cp932"); j+=2; continue
            except: pass
        if 0x20<=c<0x7f: out+=chr(c)
        elif c==0: out+="·"
        else: out+=f"[{c:02x}]"
        j+=1
    w.write(out+"\n")
w.close()
print("done")
