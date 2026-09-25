import struct, io, sys
OUT=sys.argv[1]
def readable(win):
    out="";j=0
    while j<len(win):
        c=win[j]
        if (0x81<=c<=0x9f or 0xe0<=c<=0xef) and j+1<len(win):
            try: out+=win[j:j+2].decode("cp932"); j+=2; continue
            except: pass
        if 0x20<=c<0x7f: out+=chr(c)
        elif c==0: out+="·"
        else: out+=f"[{c:02x}]"
        j+=1
    return out
w=io.open(OUT+"/container.txt","w",encoding="utf-8")
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
a,b=tbl[11]; f.seek(a*0x800); d=f.read(b)
marker,count=struct.unpack("<II",d[:8])
w.write(f"idx=11 size={b} marker={marker:#x} count={count}\n")
w.write("first 96 bytes hex:\n"+d[:96].hex()+"\n")
w.write("u32 table @0x20 (24 vals):\n"+" ".join(f"{struct.unpack('<I',d[0x20+i*4:0x24+i*4])[0]:#x}" for i in range(24))+"\n")
w.write("\n-- region 0x5c0..0x820 --\n"+readable(d[0x5c0:0x820])+"\n")
w.close(); print("done")
