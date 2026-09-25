# -*- coding: utf-8 -*-
"""RAM(eeMemory.bin)에서 화면에 보이는 무장이름(張角·何進 등)을 인코딩별로 검색.
시나리오선택 화면 상태 → 이 이름들이 RAM에 반드시 있다. 어떤 형태인지 규명."""
import os, struct

RAM = r"work\state01\eeMemory.bin"
SLPM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01"

d = open(SLPM,"rb").read()
TBL=0x4389E0; N=0x2c00
tab=struct.unpack_from("<%dH"%N,d,TBL)
def sidx(c):
    if 0x8100<=c<=0x9fff: return c-0x8100
    if 0xe000<=c<=0xeaff: return c-0xC100
    if 0xed00<=c<=0xeeff: return c-0xC300
    return c-0xC400
def slot(ch):
    c=struct.unpack(">H",ch.encode("cp932"))[0]; i=sidx(c)
    return tab[i] if 0<=i<N and tab[i]!=0xffff else None

ram=open(RAM,"rb").read()
print(f"RAM {len(ram):,}B")

# 화면표시 무장 (시나리오선택 통치자)
NAMES=["張角","何進","劉備","曹操","孫堅","董卓","袁紹","公孫"]
def findall(hay,needle,limit=20):
    out=[];i=hay.find(needle)
    while i!=-1 and len(out)<limit:
        out.append(i);i=hay.find(needle,i+1)
    return out

for nm in NAMES:
    try:
        sj=nm.encode("cp932")
    except:
        print(f"{nm}: cp932불가"); continue
    hits_sj=findall(ram,sj)
    # 슬롯 u16 페어 LE/BE
    slots=[slot(c) for c in nm]
    line=f"{nm}: SJIS={len(hits_sj)}"
    if all(s is not None for s in slots):
        le=b"".join(struct.pack("<H",s) for s in slots)
        be=b"".join(struct.pack(">H",s) for s in slots)
        line+=f"  slotLE={len(findall(ram,le))} slotBE={len(findall(ram,be))} (slots={slots})"
    print(line)
    if hits_sj:
        print(f"    SJIS첫히트 @0x{hits_sj[0]:x}, 처음5: {[hex(h) for h in hits_sj[:5]]}")
