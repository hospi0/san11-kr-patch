# -*- coding: utf-8 -*-
"""로스터 = 고정 stride 레코드. 여러 무장 full-name의 RAM 주소를 모아
인접 주소 간격(stride)이 일정한 배열(=로스터)이 있는지 본다."""
import collections
RAM=r"work\state01\eeMemory.bin"
ram=open(RAM,"rb").read()
NAMES=["曹操","劉備","孫権","関羽","張飛","趙雲","周瑜","袁紹","馬超","黄忠",
       "諸葛亮","司馬懿","呂布","董卓","孫堅","孫策","夏侯惇","張遼","趙","龐"]
addrs=[]
for nm in NAMES:
    try: sj=nm.encode("cp932")
    except: continue
    i=ram.find(sj)
    while i!=-1:
        addrs.append((i,nm)); i=ram.find(sj,i+1)
addrs.sort()
print(f"총 {len(addrs)} 히트")
# 인접 간격 히스토그램 (같은 클러스터 내)
gaps=collections.Counter()
for (a,_),(b,_) in zip(addrs,addrs[1:]):
    d=b-a
    if 8<=d<=512: gaps[d]+=1
print("인접간격(8~512) top15:", gaps.most_common(15))
# 클러스터별로 stride 규칙성 보기: 연속 히트가 일정 stride면 로스터
print("\n=== 주소 나열(클러스터 경계 보기) ===")
prev=0
for a,nm in addrs:
    mark=" <<<" if a-prev>0x1000 else ""
    print(f"0x{a:07x} {nm}{mark}")
    prev=a
