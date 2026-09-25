import struct, sys, re
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
# search each entry head + whole-archive scan for texture magics
mags=[b'TIM2',b'TIM3',b'CLT2',b'TEX2',b'GIM ',b'MTX2',b'PLT2',b'FNT',b'FONT']
# whole-file scan (chunked)
found={m:0 for m in mags}
locs={m:[] for m in mags}
with open("s11pkres.bin","rb") as g:
    base=0; prev=b""
    while True:
        c=g.read(1<<24)
        if not c: break
        data=prev+c
        for m in mags:
            for mm in re.finditer(re.escape(m),data):
                found[m]+=1
                if len(locs[m])<5: locs[m].append(base+mm.start()-len(prev))
        prev=c[-8:]; base+=len(c)
for m in mags:
    print(m, found[m], [hex(x) for x in locs[m]])
# also search executable
exe=open("SLPM_667.01","rb").read()
print("\n-- exe --")
for m in mags:
    c=exe.count(m)
    if c: print(m, c, [hex(exe.find(m))])
