import struct, re, io, sys
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10)
tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]

# JP run detector on raw bytes: count runs of >=6 consecutive full-width SJIS JP chars
jp_lead=lambda b: (0x88<=b<=0x9f or 0xe0<=b<=0xea)  # kanji/kana lead bytes (skip 0x81-0x87 symbols)
def score(d):
    runs=0; i=0; N=len(d); best=0; cur=0
    while i<N-1:
        b=d[i]
        if jp_lead(b) and 0x40<=d[i+1]<=0xfc and d[i+1]!=0x7f:
            cur+=1; i+=2
        else:
            if cur>=6: runs+=1
            best=max(best,cur); cur=0; i+=1
    if cur>=6: runs+=1
    best=max(best,cur)
    return runs, best

results=[]
for i,(a,b) in enumerate(tbl):
    if b<64 or b>4_000_000: continue
    f.seek(a*0x800); d=f.read(b)
    r,best=score(d)
    if r>=5:
        results.append((r,best,i,b,d[:8]))
results.sort(reverse=True)
with io.open(OUT+"/textscan.txt","w",encoding="utf-8") as w:
    w.write(f"entries with many JP runs (raw, uncompressed):\n")
    for r,best,i,b,h in results[:40]:
        mg=''.join(chr(x) if 32<=x<127 else '.' for x in h)
        w.write(f" idx={i:5} size={b:>10,} jp_runs={r:5} longest={best:4} magic='{mg}'\n")
    # dump a coherent sample from the top entry
    if results:
        r,best,i,b,h=results[0]
        f.seek(tbl[i][0]*0x800); d=f.read(tbl[i][1])
        # extract longest JP string
        w.write(f"\n--- sample decoded text from idx={i} ---\n")
        for m in re.finditer(rb'(?:[\x88-\x9f\xe0-\xea][\x40-\xfc]){8,}', d):
            try: w.write(m.group().decode('cp932')+"\n")
            except: pass
            if m.start()>200000: break
print("done", len(results))
