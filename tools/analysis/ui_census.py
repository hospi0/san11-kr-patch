# -*- coding: utf-8 -*-
"""SLPM_667.01 UI 텍스트 census. 널종료 SJIS/ASCII 문자열을 전수 수집해
UI 텍스트 규모·분포·영역을 측정한다."""
import sys, struct
SLPM=r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01"
d=open(SLPM,"rb").read()

def is_sjis_lead(c): return 0x81<=c<=0x9f or 0xe0<=c<=0xef
def try_str(off):
    """off부터 유효 문자열(SJIS2byte or 반각영숫자/카타카나) 파싱. (문자열, 바이트길이, 일본어글자수)"""
    j=off; s=[]; jp=0
    while j<len(d):
        c=d[j]
        if c==0: break
        if is_sjis_lead(c) and j+1<len(d):
            try:
                ch=d[j:j+2].decode("cp932"); s.append(ch); jp+=1; j+=2; continue
            except: pass
        if 0x20<=c<0x7f or 0xa1<=c<=0xdf:  # 반각 ASCII/카타카나
            s.append(chr(c) if c<0x7f else "."); j+=1; continue
        return None
    return ("".join(s), j-off, jp) if s else None

# 스캔: 널 뒤에서 시작하는 문자열, 일본어 2글자 이상 포함하는 것만 UI후보
strings=[]
i=0
while i<len(d)-2:
    if is_sjis_lead(d[i]):
        r=try_str(i)
        if r and r[2]>=2 and r[1]>=4:  # 일본어 2자↑
            strings.append((i, r[0], r[1], r[2]))
            i+=r[1]
            continue
    i+=1

# 영역 분포 (0x10000 단위 히스토그램)
from collections import Counter
region=Counter()
total_jp=0
for off,s,blen,jp in strings:
    region[off>>16]+=1; total_jp+=jp
print(f"UI 문자열(일본어2자↑) 총 {len(strings)}개, 일본어 {total_jp}자")
print(f"파일범위 0x0~0x{len(d):x}")
print("\n=== 0x10000단위 문자열 밀도 (히트10개↑ 영역) ===")
for blk in sorted(region):
    if region[blk]>=10:
        print(f"  0x{blk:03x}0000: {region[blk]}개")
print("\n=== 샘플 (0x443000~0x460000 영역 처음 40개) ===")
n=0
for off,s,blen,jp in strings:
    if 0x443000<=off<0x460000:
        print(f"  0x{off:06x} ({blen:2d}B/{jp}자): {s[:30]}")
        n+=1
        if n>=40: break
