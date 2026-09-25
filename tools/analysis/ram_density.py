# -*- coding: utf-8 -*-
"""RAM 전체를 슬라이딩윈도우로 성씨-SJIS 밀도 스캔 → 로스터급 밀집영역 탐색."""
import struct
RAM=r"work\state01\eeMemory.bin"
ram=open(RAM,"rb").read()
SURN=["曹","劉","孫","張","司","夏","諸","袁","馬","王","李","陳","趙","周","呂","関","黄","徐","甘","楊","趙","黄","魏","呉","蜀"]
SURB=[s.encode("cp932") for s in set(SURN)]

# 4KB 윈도우, 2KB step
WIN=0x1000; STEP=0x800
best=[]
for base in range(0,len(ram)-WIN,STEP):
    w=ram[base:base+WIN]
    c=sum(w.count(s) for s in SURB)
    if c>=8:
        best.append((c,base))
best.sort(reverse=True)
print("=== 성씨밀도 4KB윈도우 top30 (cnt,addr) ===")
for c,base in best[:30]:
    print(f"  cnt={c:4d} @0x{base:07x}")
print(f"\n총 {len(best)} 윈도우가 성씨>=8")
