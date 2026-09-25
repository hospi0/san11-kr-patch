# -*- coding: utf-8 -*-
"""중첩 LINK 재귀 성씨-밀도 스캔. census가 '산문 0'으로 버린 leaf 중
한자(성씨) 밀도가 높은 leaf = 로스터 후보를 찾는다.
"""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from link import Link
from deep_census import parse_link, MAX_DEPTH

ARC = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\s11pkres.bin"
SURN = ["曹","劉","孫","張","司","夏","諸","袁","馬","王","李","陳","趙","周","呂","関","黄","徐","甘","楊"]
SURB = [s.encode("cp932") for s in SURN]

def sur_count(b):
    return sum(b.count(s) for s in SURB)

leaves=[]
def walk(b, path, depth):
    subs = parse_link(b) if depth < MAX_DEPTH else None
    if subs:
        for i,(off,sz) in enumerate(subs):
            walk(b[off:off+sz], path+[i], depth+1)
        return
    if len(b) < 128: return
    c = sur_count(b)
    if c >= 10:
        leaves.append(('.'.join(map(str,path)), len(b), c, c*2/len(b)))

arc = Link(ARC)
for i in range(arc.count):
    walk(arc.read(i), [i], 0)

leaves.sort(key=lambda r: -r[3])  # density
print("=== 성씨밀도 top30 leaf (path, size, surcnt, density) ===")
for p,sz,c,dn in leaves[:30]:
    print(f"  {p:18s} size={sz:9d} sur={c:5d} dens={dn:.4f}")
print(f"\n총 {len(leaves)} leaf가 성씨>=10")
