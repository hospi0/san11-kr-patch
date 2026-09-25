# -*- coding: utf-8 -*-
"""무장 로스터 탐색 프로브 — Overlay1/2 + SLPM 대상.
姓/名 별도 필드 가설 검증: 성 글자와 명 글자의 위치 분포·stride를 본다.
"""
import sys, os, collections

BASE = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
FILES = {
    "Overlay1": os.path.join(BASE, "Overlay1.bin"),
    "Overlay2": os.path.join(BASE, "Overlay2.bin"),
    "SLPM":     os.path.join(BASE, "SLPM_667.01"),
}

# 유명 무장: (성, 명) — SJIS로 인코딩해 바이트 검색
GENERALS = [
    ("曹","操"), ("劉","備"), ("孫","権"), ("関","羽"), ("張","飛"),
    ("諸","亮"), ("呂","布"), ("趙","雲"), ("周","瑜"), ("袁","紹"),
    ("馬","超"), ("黄","忠"), ("荀","彧"), ("郭","嘉"), ("司","懿"),
]

def enc(ch):
    return ch.encode("cp932")

def find_all(data, needle):
    out=[]; i=data.find(needle)
    while i!=-1:
        out.append(i); i=data.find(needle, i+1)
    return out

for name, path in FILES.items():
    data = open(path,"rb").read()
    print(f"\n===== {name}  ({len(data):,} B) =====")
    # 각 성 글자 위치 수집
    surname_hits = {}
    for sur, giv in GENERALS:
        sh = find_all(data, enc(sur))
        gh = find_all(data, enc(giv))
        surname_hits[sur] = sh
        # 성 바로 뒤 or 근처(stride 후보)에 명이 오는지
        near = 0
        for p in sh:
            for d in range(2, 16, 2):  # 성 뒤 2~14바이트 내 짝수위치
                if data[p+d:p+d+2] == enc(giv):
                    near += 1
                    break
        print(f"  {sur}{giv}: 성{len(sh):4d}회 명{len(gh):4d}회  성뒤근접(2~14B)={near}")
    # 성 글자들이 밀집 클러스터를 이루는가? 전체 성 히트를 정렬해 인접 간격 히스토그램
    allsur = sorted(p for sh in surname_hits.values() for p in sh)
    if len(allsur) > 5:
        gaps = collections.Counter(b-a for a,b in zip(allsur, allsur[1:]) if 0 < b-a <= 64)
        print(f"  전체 성히트={len(allsur)}, 인접간격 top: {gaps.most_common(8)}")
