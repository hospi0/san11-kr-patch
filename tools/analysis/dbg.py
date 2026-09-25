from capstone import *
exe=open("SLPM_667.01","rb").read()
code=exe[0x100:0x100+0x400]
for mode in [CS_MODE_MIPS32, CS_MODE_MIPS64]:
    md=Cs(CS_ARCH_MIPS, mode+CS_MODE_LITTLE_ENDIAN)
    cnt=0
    print(f"--- mode {mode} ---")
    for insn in md.disasm(code,0x100000):
        if cnt<14: print(f" 0x{insn.address:x}: {insn.mnemonic} {insn.op_str}")
        cnt+=1
    print("  total decoded:",cnt)
