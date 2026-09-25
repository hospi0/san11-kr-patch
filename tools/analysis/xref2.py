import sys, io, struct
from capstone import *
OUT=sys.argv[1]
exe=open("SLPM_667.01","rb").read()
BASE=0x100000; FOFF=0x100; CODELEN=0x340000
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS64+CS_MODE_LITTLE_ENDIAN)
code=exe[FOFF:FOFF+CODELEN]
lui={}; refs=[]
pos=0; N=len(code)
def parse(op): return op.replace(',',' ').replace('(',' ').replace(')',' ').split()
while pos<N-4:
    got=False
    for insn in md.disasm(code[pos:pos+8], BASE+pos):
        got=True; m=insn.mnemonic; p=parse(insn.op_str); va=insn.address
        try:
            if m=="lui" and len(p)>=2:
                lui[p[0]]=(int(p[1],16)<<16 if p[1].startswith("0x") else int(p[1])<<16, va)
            elif m in ("addiu","ori","daddiu") and len(p)>=3 and p[1] in lui:
                v=int(p[2],16) if p[2].startswith(("0x","-0x")) else int(p[2])
                addr=(lui[p[1]][0]+v)&0xffffffff
                if 0x53E500<=addr<0x53E540: refs.append((va,addr,'addr'))
        except: pass
        pos+=insn.size; break
    if not got: pos+=4
w=io.open(OUT+"/xref2.txt","w",encoding="utf-8")
w.write(f"refs to atlas-upload descriptor 0x53E500-0x53E540: {len(refs)}\n")
for va,addr,k in refs: w.write(f"  code@0x{va:x} -> 0x{addr:x}\n")
# dump descriptor block interpreted as u32
w.write("\ndescriptor block VA 0x53E500..0x53E5C0:\n")
d=exe[0x53E500-0xfff00:0x53E5C0-0xfff00]
for i in range(0,len(d),16):
    w.write(f"  0x{0x53E500+i:x}: "+" ".join(f"{x:08x}" for x in struct.unpack('<4I',d[i:i+16]))+"\n")
w.close()
print(io.open(OUT+"/xref2.txt",encoding="utf-8").read())
