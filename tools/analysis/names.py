import re, io, sys, collections
OUT=sys.argv[1]
# scan whole archive in chunks for ASCII tags like KOEI%XXX and 4-8 letter magics
tags=collections.Counter()
koei=collections.Counter()
with open("s11pkres.bin","rb") as f:
    prev=b""
    while True:
        chunk=f.read(1<<24)
        if not chunk: break
        data=prev+chunk
        for m in re.finditer(rb'KOEI%[A-Za-z0-9_]{1,12}', data):
            koei[m.group().decode()]+=1
        prev=chunk[-16:]
with io.open(OUT+"/names.txt","w",encoding="utf-8") as w:
    w.write(f"distinct KOEI%% tags: {len(koei)}\n")
    for k,c in koei.most_common():
        w.write(f"  {c:5}  {k}\n")
print("KOEI tags:",len(koei))
