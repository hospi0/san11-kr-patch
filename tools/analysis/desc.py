import struct
exe=open("SLPM_667.01","rb").read()
def rd(va, ln): 
    f=va-0xfff00; return exe[f:f+ln]
for va in [0x53E520,0x53E560,0x53E5A0]:
    d=rd(va,0x40)
    print(f"VA 0x{va:x} (file 0x{va-0xfff00:x}):")
    for i in range(0,0x40,16):
        words=struct.unpack("<4I", d[i:i+16])
        print("   "+ " ".join(f"{w:08x}" for w in words))
# also dump font struct header VA 0x538000
print("\nfont struct VA 0x538000:")
d=rd(0x538000,0x40)
for i in range(0,0x40,16):
    print("   "+" ".join(f"{w:08x}" for w in struct.unpack("<4I",d[i:i+16])))
# SJIS->slot table sample at 0x5388E0
print("\nSJIS->slot table VA 0x5388e0 (first 32 u16):")
d=rd(0x5388E0,64)
print("   "+" ".join(f"{v:04x}" for v in struct.unpack("<32H",d)))
