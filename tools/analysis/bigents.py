import struct, sys
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
# entries 85..100 details
for i in list(range(85,100)):
    a,b=tbl[i]; f.seek(a*0x800); h=f.read(32)
    print(f"idx={i} size={b:>10,} magic={h[:8].hex()} head={h.hex()}")
