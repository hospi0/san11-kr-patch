import io, sys
OUT=sys.argv[1]
names=["曹操","劉備","孫権","諸葛亮","関羽","張飛","呂布","武将","都市","兵力","武力","知力","董卓","袁紹"]
pats=[(nm, nm.encode("cp932")) for nm in names]
def scan(data):
    res={}
    for nm,b in pats:
        idxs=[]; start=0
        while True:
            j=data.find(b,start)
            if j<0: break
            idxs.append(j); start=j+1
            if len(idxs)>=6: break
        res[nm]=(data.count(b), idxs)
    return res
w=io.open(OUT+"/names_result.txt","w",encoding="utf-8")
for path in ["SLPM_667.01","Overlay1.bin","Overlay2.bin","s11pkres.bin"]:
    data=open(path,"rb").read()
    r=scan(data)
    w.write(f"\n== {path} ({len(data):,} bytes) ==\n")
    for nm,b in pats:
        c,idxs=r[nm]
        w.write(f"  {nm} [{b.hex()}]: {c} hits  @ {[hex(x) for x in idxs[:4]]}\n")
w.close()
print("done")
