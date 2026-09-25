# -*- coding: utf-8 -*-
"""최장 '연속 한자 런' 검출기. 이름 한자테이블은 히라가나 없이 한자만 길게 이어진다.
산문은 히라가나가 자주 끊고, 이미지는 유효 SJIS 런이 짧다.
각 leaf: 최장 연속 2byte-SJIS-한자 런 길이(문자수)를 잰다.
"""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from link import Link
from deep_census import parse_link, MAX_DEPTH

ARC = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\s11pkres.bin"

def is_kanji_lead(b0, b1):
    # SJIS 2-byte 한자(제1수준~제2수준 대략): lead 0x88-0x9F,0xE0-0xEA
    if not (0x88 <= b0 <= 0x9F or 0xE0 <= b0 <= 0xEA): return False
    if not (0x40 <= b1 <= 0xFC and b1 != 0x7F): return False
    return True

def longest_kanji_run(b):
    """(최장 고유율높은런 문자수, 시작오프셋, 고유율). 반복바이트 노이즈 배제.
    각 연속 한자런에서 distinct/len>=0.4 인 것만 후보. 노이즈는 고유율 낮다."""
    best=0; best_at=0; best_var=0.0
    i=0; n=len(b)
    while i < n-1:
        if is_kanji_lead(b[i], b[i+1]):
            start=i; chars=[]
            while i < n-1 and is_kanji_lead(b[i], b[i+1]):
                chars.append(b[i:i+2]); i+=2
            L=len(chars); var=len(set(chars))/L if L else 0
            if L>=20 and var>=0.4 and L>best:
                best=L; best_at=start; best_var=var
        else:
            i+=1
    return best, best_at, best_var

leaves=[]
def walk(b, path, depth):
    subs = parse_link(b) if depth < MAX_DEPTH else None
    if subs:
        for i,(off,sz) in enumerate(subs):
            walk(b[off:off+sz], path+[i], depth+1)
        return
    if len(b) < 256: return
    run, at, var = longest_kanji_run(b)
    if run >= 30:
        leaves.append(('.'.join(map(str,path)), len(b), run, at, var))

arc = Link(ARC)
for i in range(arc.count):
    walk(arc.read(i), [i], 0)

leaves.sort(key=lambda r: -r[2])
print("=== 고유율>=0.4 최장한자런 top30 (path, size, run, at, var) ===")
for p,sz,run,at,var in leaves[:30]:
    print(f"  {p:18s} size={sz:9d} run={run:5d}자 @0x{at:x} var={var:.2f}")
print(f"\n총 {len(leaves)} leaf")
