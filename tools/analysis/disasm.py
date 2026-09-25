import struct, sys, collections
from capstone import *
OUT=sys.argv[1]
exe=open("SLPM_667.01","rb").read()
BASE=0x100000; FOFF=0x100
code=exe[FOFF:FOFF+0x340000]  # 0x100000..0x440000 VA (code region, before data)
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
md.detail=True
SJIS={0x81,0x9f,0xa0,0xdf,0xe0,0xfc,0x7f}
STRIDE={0xbc,188,72,0x48,32,0x18,24,144,0x90}
hits_sjis=[]   # (va, mnemonic, imm)
hits_stride=[]
for insn in md.disasm(code, BASE):
    op=insn.op_str
    # crude immediate parse
    if insn.mnemonic in ("sltiu","slti","addiu","andi","ori","xori","li","sll"):
        # find last token as imm
        parts=op.replace(',',' ').split()
        for tok in parts:
            try:
                v=int(tok,16) if tok.startswith("0x") else (int(tok) if tok.lstrip('-').isdigit() else None)
            except: v=None
            if v is None: continue
            if v in SJIS: hits_sjis.append((insn.address,insn.mnemonic,v))
            if v in STRIDE: hits_stride.append((insn.address,insn.mnemonic,v))
print("sjis-const hits:",len(hits_sjis)," stride hits:",len(hits_stride))
# cluster sjis hits by proximity (within 0x80 bytes) and rank clusters that contain multiple distinct sjis consts
hits_sjis.sort()
clusters=[]
cur=[]
for h in hits_sjis:
    if cur and h[0]-cur[-1][0]>0x60:
        clusters.append(cur); cur=[]
    cur.append(h)
if cur: clusters.append(cur)
scored=[]
for c in clusters:
    consts=set(x[2] for x in c)
    key=len(consts& {0x81,0x9f,0xe0,0xa0,0xdf})
    scored.append((key,len(c),c[0][0],c[-1][0],sorted(consts)))
scored.sort(reverse=True)
w=open(OUT+"/disasm.txt","w",encoding="utf-8")
w.write("TOP SJIS-decode candidate clusters (VA range, distinct boundary consts):\n")
for key,ln,a,b,consts in scored[:15]:
    w.write(f"  score={key} n={ln} VA 0x{a:x}..0x{b:x} consts={[hex(x) for x in consts]}\n")
w.close()
open(OUT+"/disasm.txt").read()
print("wrote disasm.txt")
import io
print(io.open(OUT+"/disasm.txt",encoding="utf-8").read())
