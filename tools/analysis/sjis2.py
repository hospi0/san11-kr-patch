import re, io, sys
OUT=sys.argv[1]
def sjis_strings(path, minlen=4):
    data=open(path,"rb").read()
    out=[]; i=0; N=len(data); cur=bytearray()
    while i<N:
        b=data[i]
        if 0x20<=b<0x7f:
            cur.append(b); i+=1; continue
        if (0x81<=b<=0x9f or 0xe0<=b<=0xef) and i+1<N:
            b2=data[i+1]
            if 0x40<=b2<=0xfc and b2!=0x7f:
                cur+=data[i:i+2]; i+=2; continue
        if len(cur)>=minlen:
            try:
                s=cur.decode("cp932")
                if re.search(r'[぀-ヿ一-鿿]', s):
                    out.append((i-len(cur),s))
            except: pass
        cur=bytearray(); i+=1
    return out

with io.open(OUT+"/jp_strings.txt","w",encoding="utf-8") as w:
    for path in ["SLPM_667.01","Overlay1.bin","Overlay2.bin"]:
        ss=sjis_strings(path)
        ss=[(o,s) for o,s in ss if len(re.findall(r'[぀-ヿ一-鿿]',s))>=2]
        w.write(f"\n===== {path}: {len(ss)} JP strings =====\n")
        for off,s in ss[:150]:
            w.write(f"  @0x{off:06x}: {s[:70]}\n")
print("done")
