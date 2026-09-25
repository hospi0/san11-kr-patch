# -*- coding: utf-8 -*-
"""이름이 SJIS가 아니라 '슬롯 인덱스(u16)'로 저장됐다는 가설 검증.
무장 성+명 글자의 슬롯번호를 계산 → 그 u16 페어를 전 파일에서 LE/BE로 검색.
"""
import os, struct, mmap

BASE_DIR = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
SLPM = os.path.join(BASE_DIR, "SLPM_667.01")

d = open(SLPM,"rb").read()
TBL = 0x4389E0; N = 0x2c00
tab = struct.unpack_from("<%dH"%N, d, TBL)
def sidx(c):
    if 0x8100<=c<=0x9fff: return c-0x8100
    if 0xe000<=c<=0xeaff: return c-0xC100
    if 0xed00<=c<=0xeeff: return c-0xC300
    return c-0xC400
def slot(ch):
    c = struct.unpack(">H", ch.encode("cp932"))[0]
    i = sidx(c)
    return tab[i] if 0<=i<N and tab[i]!=0xffff else None

GENERALS = [("曹","操"),("劉","備"),("孫","権"),("関","羽"),("張","飛"),
            ("呂","布"),("趙","雲"),("周","瑜"),("袁","紹"),("馬","超")]

print("무장 슬롯번호:")
pairs=[]
for sur,giv in GENERALS:
    s1,s2 = slot(sur), slot(giv)
    print(f"  {sur}(slot {s1})  {giv}(slot {s2})")
    if s1 is not None and s2 is not None:
        pairs.append((sur+giv, s1, s2))

FILES = {
    "s11pkres": os.path.join(BASE_DIR,"s11pkres.bin"),
    "SLPM": SLPM,
    "Overlay1": os.path.join(BASE_DIR,"Overlay1.bin"),
    "Overlay2": os.path.join(BASE_DIR,"Overlay2.bin"),
}
for fname, path in FILES.items():
    data = open(path,"rb").read()
    print(f"\n=== {fname} ({len(data):,}B) ===")
    for nm,s1,s2 in pairs:
        le = struct.pack("<HH", s1, s2)
        be = struct.pack(">HH", s1, s2)
        cle = data.count(le); cbe = data.count(be)
        # 단일 슬롯 u16 (성) LE 빈도도
        c_s1 = data.count(struct.pack("<H", s1))
        print(f"  {nm}: pairLE={cle:4d} pairBE={cbe:4d}   성단독u16LE={c_s1}")
