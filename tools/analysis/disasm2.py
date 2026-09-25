import sys, io
from capstone import *
OUT=sys.argv[1]
exe=open("SLPM_667.01","rb").read()
BASE=0x100000; FOFF=0x100
CODELEN=0x340000
code=exe[FOFF:FOFF+CODELEN]
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS64+CS_MODE_LITTLE_ENDIAN)
SJIS={0x81,0x9f,0xa0,0xdf,0xe0,0xfc}
STRIDE={0xbc,72,32,24,144,96,0x30,384,0x180}
sjis_hits=[]; stride_hits=[]; total=0
pos=0; N=len(code)
sample=[]
while pos < N-4:
    got=False
    for insn in md.disasm(code[pos:pos+4096], BASE+pos):
        got=True; total+=1
        if len(sample)<14 and BASE+pos>0x100008: sample.append(f"0x{insn.address:x}: {insn.mnemonic} {insn.op_str}")
        o=insn.op_str
        for tok in o.replace(',',' ').split():
            v=None
            try:
                if tok.startswith("0x"): v=int(tok,16)
                elif tok.lstrip('-').isdigit(): v=int(tok)&0xffffffff
            except: v=None
            if v is None: continue
            if v in SJIS: sjis_hits.append((insn.address,insn.mnemonic,v,o))
            if v in STRIDE: stride_hits.append((insn.address,insn.mnemonic,v,o))
        pos+=insn.size
    if not got: pos+=4
w=io.open(OUT+"/disasm.txt","w",encoding="utf-8")
w.write(f"decoded ~{total} insns; sjis_hits={len(sjis_hits)} stride_hits={len(stride_hits)}\n")
w.write("sample:\n"+"\n".join(sample)+"\n")
# cluster sjis hits
sjis_hits.sort()
clusters=[]; cur=[]
for h in sjis_hits:
    if cur and h[0]-cur[-1][0]>0x80: clusters.append(cur); cur=[]
    cur.append(h)
if cur: clusters.append(cur)
scored=[]
for c in clusters:
    consts=set(x[2] for x in c)
    scored.append((len(consts&{0x81,0x9f,0xe0,0xa0,0xdf}), c[0][0], c[-1][0], sorted(consts), len(c)))
scored.sort(reverse=True)
w.write("\nTOP SJIS clusters:\n")
for k,a,b,consts,ln in scored[:12]:
    w.write(f"  score={k} VA 0x{a:x}..0x{b:x} n={ln} consts={[hex(x) for x in consts]}\n")
w.close()
print(io.open(OUT+"/disasm.txt",encoding="utf-8").read()[:2000])
