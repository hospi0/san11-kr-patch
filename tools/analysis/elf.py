import struct
exe=open("SLPM_667.01","rb").read()
assert exe[:4]==b'\x7fELF'
e_entry,e_phoff=struct.unpack("<II",exe[0x18:0x20])
e_phentsize,e_phnum=struct.unpack("<HH",exe[0x2a:0x2e])
print(f"entry={e_entry:#x} phoff={e_phoff:#x} phnum={e_phnum} phentsize={e_phentsize}")
segs=[]
for i in range(e_phnum):
    off=e_phoff+i*e_phentsize
    p_type,p_off,p_vaddr,p_paddr,p_filesz,p_memsz,p_flags,p_align=struct.unpack("<IIIIIIII",exe[off:off+32])
    segs.append((p_type,p_off,p_vaddr,p_filesz,p_memsz,p_flags))
    print(f"  seg{i}: type={p_type} off={p_off:#x} vaddr={p_vaddr:#x} filesz={p_filesz:#x} memsz={p_memsz:#x} flags={p_flags}")
# map file 0x443c00 to VA using LOAD seg containing it
for t,o,v,fs,ms,fl in segs:
    if t==1 and o<=0x443c00<o+fs:
        print(f"text pool file 0x443c00 -> VA {v + (0x443c00-o):#x}")
