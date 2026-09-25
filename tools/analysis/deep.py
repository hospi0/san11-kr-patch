import sys, io
from capstone import *
OUT=sys.argv[1]
exe=open("SLPM_667.01","rb").read()
BASE=0x100000; FOFF=0x100
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS64+CS_MODE_LITTLE_ENDIAN)
def dis(va0, va1):
    out=[]
    pos=va0-BASE
    while pos < va1-BASE:
        got=False
        for insn in md.disasm(exe[FOFF+pos:FOFF+pos+64], BASE+pos):
            out.append(f"0x{insn.address:x}: {insn.mnemonic:10} {insn.op_str}")
            pos+=insn.size; got=True; break
        if not got:
            out.append(f"0x{BASE+pos:x}: .word 0x{int.from_bytes(exe[FOFF+pos:FOFF+pos+4],'little'):08x}")
            pos+=4
    return out
w=io.open(OUT+"/deep.txt","w",encoding="utf-8")
for a,b in [(0x16b9c0,0x16bc40),(0x17f240,0x17f420),(0x16c120,0x16c220)]:
    w.write(f"\n========== VA 0x{a:x}..0x{b:x} ==========\n")
    w.write("\n".join(dis(a,b))+"\n")
w.close()
print(io.open(OUT+"/deep.txt",encoding="utf-8").read())
