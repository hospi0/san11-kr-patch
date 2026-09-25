# -*- coding: utf-8 -*-
"""state02(武将情報 화면)에서 로스터 찾기. 화면의 무장이름을 검색하고 stride 분석."""
import collections
RAM=r"work\state02\eeMemory.bin"
ram=open(RAM,"rb").read()
# 화면 왼쪽 목록 순서
SCREEN=["于禁","袁遺","袁胤","袁熙","閻行","閻柔","袁術","袁紹","閻象","袁譚","閻圃","王允","王匡","王修"]
def findall(needle,limit=40):
    out=[];i=ram.find(needle)
    while i!=-1 and len(out)<limit:
        out.append(i);i=ram.find(needle,i+1)
    return out
print("=== 화면 무장이름 RAM 위치 ===")
allhits=[]
for nm in SCREEN:
    sj=nm.encode("cp932")
    hits=findall(sj)
    allhits+=[(h,nm) for h in hits]
    print(f"{nm}: {len(hits)}회  {[hex(h) for h in hits[:6]]}")
allhits.sort()
# 밀집 영역: 연속 히트가 몰린 곳
print("\n=== 인접 히트 간격(같은 로스터면 일정 stride) ===")
prev=None
for a,nm in allhits:
    d=a-prev if prev is not None else 0
    if prev is not None and d<0x400:
        print(f"0x{a:07x} {nm}  (+0x{d:x})")
    else:
        print(f"0x{a:07x} {nm}  ---경계---")
    prev=a
