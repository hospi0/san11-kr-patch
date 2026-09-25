import sys, io
from capstone import *
OUT=sys.argv[1]
exe=open("SLPM_667.01","rb").read()
BASE=0x100000; FOFF=0x100; CODELEN=0x340000
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS64+CS_MODE_LITTLE_ENDIAN); md.detail=False
# Track lui then addiu/ori/lw per register to reconstruct addresses in font data region
code=exe[FOFF:FOFF+CODELEN]
lui={}   # reg -> (hi, va)
refs=[]
pos=0; N=len(code)
def parse(op):
    return op.replace(',',' ').replace('(',' ').replace(')',' ').split()
while pos<N-4:
    got=False
    for insn in md.disasm(code[pos:pos+8], BASE+pos):
        got=True; m=insn.mnemonic; p=parse(insn.op_str); va=insn.address
        try:
            if m=="lui" and len(p)>=2:
                reg=p[0]; imm=int(p[1],16) if p[1].startswith("0x") else int(p[1])
                lui[reg]=(imm<<16, va)
            elif m in ("addiu","ori","daddiu") and len(p)>=3 and p[1] in lui:
                base=lui[p[1]][0]; 
                imm=p[2]
                v=int(imm,16) if imm.startswith("0x") or imm.startswith("-0x") else int(imm)
                addr=(base+v)&0xffffffff
                if 0x538000<=addr<0x540000:
                    refs.append((va, addr, lui[p[1]][1]))
            elif m in ("lw","lhu","lbu","lh","lb","sw","sh","sb","ld","sd") and len(p)>=3 and p[-1] in lui:
                base=lui[p[-1]][0]
                imm=p[1]
                try: v=int(imm,16) if imm.startswith(("0x","-0x")) else int(imm)
                except: v=0
                addr=(base+v)&0xffffffff
                if 0x538000<=addr<0x540000:
                    refs.append((va, addr, lui[p[-1]][1]))
        except: pass
        pos+=insn.size; break
    if not got: pos+=4
w=io.open(OUT+"/xref.txt","w",encoding="utf-8")
w.write(f"xrefs into font data 0x538000-0x540000: {len(refs)}\n")
seen=set()
for va,addr,luiva in sorted(refs):
    w.write(f"  code@0x{va:x}  -> data VA 0x{addr:x} (file 0x{addr-0xfff00:x})\n")
w.close()
print(io.open(OUT+"/xref.txt",encoding="utf-8").read()[:3000])
